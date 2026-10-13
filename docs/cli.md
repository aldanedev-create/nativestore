# CLI

| Command | Behavior |
| --- | --- |
| `new NAME` | Generate a real app; refuses existing directories |
| `dev` | Compile and launch Tauri, watch project files and restart |
| `dev --browser` | Start authenticated backend and open a browser debugging session |
| `dev --no-watch` | Launch once without automatic restarts |
| `test` | Run the generated project's pytest suite; preserve exit status |
| `build` | Freeze backend and create a Windows x64 NSIS installer |
| `routes` | Print a deterministic route manifest without importing handlers |
| `add NAME[@VERSION]` | Install an approved pinned browser asset with integrity verification |
| `add NAME --offline` | Install from verified cache only |
| `remove NAME` | Update lock and remove managed asset |
| `list` | Show installed locked packages |
| `update [--offline]` | Resolve newest approved registry entries, not arbitrary latest CDN versions |
| `doctor` | Report Python, cargo presence and platform |
| `--version` | Print version |

All commands also work through `python -m nativestore`. Doctor is an inventory,
not a guarantee that Visual Studio/WebView2/native libraries are installed.

The optional Rust CLI is built with `cargo build -p nativestore-cli --release`.
Its `routes` command uses Rust discovery. Other commands delegate to Python.
Set NATIVESTORE_PYTHON to choose the interpreter when using the Rust executable.
