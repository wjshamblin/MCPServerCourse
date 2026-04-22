# Step 02: Resources and Prompts

Building on the tools from step-01, this step introduces two more MCP primitives: **resources** and **prompts**.

## Resources

Resources are **read-only data** that a server exposes to clients. Unlike tools (which perform actions), resources provide information the LLM can read to inform its responses. Clients fetch resources by URI.

### Resource Types

| Type | URI Example | Description |
|------|-------------|-------------|
| **Static** | `resource://about` | Fixed content that doesn't change between reads |
| **Dynamic** | `resource://server-time` | Content generated at read time (e.g., current timestamp) |
| **Template** | `resource://greeting/{name}` | Parameterized URI — the client fills in `{name}` to get personalized content |

### Resources Defined

| Resource | URI | MIME Type | Description |
|----------|-----|-----------|-------------|
| `get_about` | `resource://about` | `text/plain` | Static server description |
| `get_server_time` | `resource://server-time` | `application/json` | Current UTC time and Unix timestamp |
| `get_greeting_resource` | `resource://greeting/{name}` | `text/plain` | Personalized greeting (template) |
| `get_server_config` | `data://server-config` | `application/json` | Server metadata and capabilities |

## Prompts

Prompts are **reusable message templates** that help clients construct common interactions. They accept parameters and return pre-formatted messages the LLM can use as conversation starters or context.

### Prompts Defined

| Prompt | Parameters | Description |
|--------|------------|-------------|
| `code_review` | `language`, `code` | Generates a code review request with the code in a fenced block |
| `summarize` | `text`, `style?` (default: `"concise"`) | Generates a summarization request with a configurable style |
| `explain_concept` | `concept`, `audience?` (default: `"beginner"`) | Generates a multi-message explanation request with a system-like setup and assistant priming |

### Prompt Return Types

Prompts can return either a plain `str` (converted to a single user message) or a `list[Message]` for multi-message sequences. The `explain_concept` prompt demonstrates multi-message prompts by including both a user message and an assistant priming message.

## Resources vs. Tools

| | Resources | Tools |
|---|-----------|-------|
| **Purpose** | Provide data for the LLM to read | Perform actions or computations |
| **Access** | Read-only | Can have side effects |
| **Invocation** | Client reads by URI | Client calls with arguments |
| **Discovery** | Listed with URIs and MIME types | Listed with names and input schemas |

## New Concepts

- **`@mcp.resource(uri)`** — Decorator that registers a function as a resource at the given URI.
- **`mime_type`** — Tells the client how to interpret the resource content (e.g., `text/plain`, `application/json`).
- **Resource templates** — URIs with `{parameter}` placeholders that the client fills in, e.g., `resource://greeting/{name}`.
- **`@mcp.prompt`** — Decorator that registers a function as a reusable prompt template.
- **`Message(content, role)`** — A prompt message. Defaults to `role="user"`. Use `role="assistant"` for priming messages that set up the assistant's response pattern.
