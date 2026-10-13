# Quickstart

Install from the source root: `python -m pip install -e ".[dev,packaging]"`.
Generate: `python -m nativestore new expense-desk`.
Enter that directory, then run `python -m nativestore dev --browser` for debugging
or `python -m nativestore dev` for a native window when prerequisites are available.

The browser debugging session is explicitly requested and uses the same authenticated
Python backend as the native shell. The startup link contains a random credential;
NativeStore opens it directly and avoids printing it to logs.

Add an expense, navigate to About, return and delete it. Close/reopen the application
to verify persistence. Run `python -m nativestore test` in the generated project.
SQLite lives under LOCALAPPDATA/NativeStore/<name> on Windows,
~/Library/Application Support/NativeStore/<name> on macOS and
$XDG_DATA_HOME/NativeStore/<name> (default ~/.local/share) on Linux.
Set NATIVESTORE_DATA_DIR to override the application data directory.

In desktop mode changing files restarts the shell and backend. Browser mode opens a
new authenticated tab on restart. Use `--no-watch` to disable restarts.
