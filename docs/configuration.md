# Configuration

```toml
[app]
name = "expense-desk"
title = "Expense Desk"
entry = "main.py"
width = 1100
height = 750
identifier = "dev.nativestore.expensedesk"
version = "0.1.0"
```

Only [app] is accepted. Unknown fields fail validation. Name is a lowercase slug;
identifier uses reverse-domain notation. Version is major.minor.patch. Dimensions
are integers from 320 to 7680. Entry must be a Python file inside the project.
The entry exports `app`, a NativeStore App. Lifecycle loading is explicit and imports
trusted application code only after route scanning. No configuration is evaluated as code.

App(title=..., frontend="static", width=..., height=..., root=..., name=...) supports
only the static frontend mode. Configuration loaded from TOML controls native window
options. Keep App's name consistent with the TOML name to select the intended data path.
Root defaults to the current working directory. Secrets must not live in templates,
static assets or packaged application source.


Optional [app] fields:

| Field | Default | Contract |
| --- | --- | --- |
| command_timeout | 30 | Caller deadline, 0.05–600 seconds |
| max_result_bytes | 1048576 | Response limit, 1024–20971520 bytes |
| request_workers | 16 | Simultaneous HTTP sockets, 1–64 |
| hidden_imports | [] | Explicit Python imports for dynamic dependencies |
| extra_resources | [] | Additional existing relative files/directories to package |
| native_features | [] | dialog, clipboard, notifications, window |

When nativestore.toml exists it is authoritative for application/window configuration.
Constructor settings are used when no project configuration exists. Data paths follow
LOCALAPPDATA on Windows, Library/Application Support on macOS and XDG_DATA_HOME on Linux.
New projects receive distinct application identifiers based on their project names.
