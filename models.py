"""Pydantic models for directory results."""

from pydantic import BaseModel


class UserResult(BaseModel):
    """Formatted user directory result."""
    id: str = ""
    display_name: str = ""
    email: str = ""
    upn: str = ""
    job_title: str = ""
    department: str = ""
    office: str = ""
    phone: str = ""

    @classmethod
    def from_graph(cls, data: dict) -> "UserResult":
        phones = data.get("businessPhones", [])
        return cls(
            id=data.get("id", ""),
            display_name=data.get("displayName", ""),
            email=data.get("mail", ""),
            upn=data.get("userPrincipalName", ""),
            job_title=data.get("jobTitle", "") or "",
            department=data.get("department", "") or "",
            office=data.get("officeLocation", "") or "",
            phone=phones[0] if phones else data.get("mobilePhone", "") or "",
        )
