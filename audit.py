"""
Audit logging with tamper-detected hash chain.

Every query is logged with a SHA-256 hash chain — each entry
includes the hash of the previous entry, making it detectable
if any log entry is modified or deleted.
"""

import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)


class AuditLogger:
    """Append-only audit log with hash chain integrity."""

    def __init__(self, log_dir: str = "logs"):
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._previous_hash = "GENESIS"

    def _current_log_path(self) -> Path:
        """Monthly log rotation."""
        month = datetime.now(timezone.utc).strftime("%Y-%m")
        return self.log_dir / f"audit-{month}.jsonl"

    def _compute_hash(self, entry: dict) -> str:
        """SHA-256 hash of the entry content."""
        content = json.dumps(entry, sort_keys=True, default=str)
        return hashlib.sha256(content.encode()).hexdigest()

    def log(
        self,
        user_email: str,
        action: str,
        detail: str = "",
        result_count: int = 0,
    ) -> None:
        """Write an audit log entry."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "user": user_email,
            "action": action,
            "detail": detail[:500],
            "result_count": result_count,
            "previous_hash": self._previous_hash,
        }
        entry["hash"] = self._compute_hash(entry)
        self._previous_hash = entry["hash"]

        log_path = self._current_log_path()
        with open(log_path, "a") as f:
            f.write(json.dumps(entry) + "\n")
            f.flush()
            os.fsync(f.fileno())

    def verify_chain(self, log_path: Path | None = None) -> tuple[bool, int]:
        """Verify the hash chain integrity of a log file.

        Returns:
            Tuple of (is_valid, entry_count).
        """
        path = log_path or self._current_log_path()
        if not path.exists():
            return True, 0

        previous_hash = "GENESIS"
        count = 0

        with open(path) as f:
            for line in f:
                entry = json.loads(line.strip())
                if entry.get("previous_hash") != previous_hash:
                    logger.error(f"Hash chain broken at entry {count}")
                    return False, count

                stored_hash = entry.pop("hash")
                computed = self._compute_hash(entry)
                if computed != stored_hash:
                    logger.error(f"Entry {count} has been tampered with")
                    return False, count

                previous_hash = stored_hash
                count += 1

        return True, count
