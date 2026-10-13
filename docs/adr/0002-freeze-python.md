# ADR 2: Freeze Python as a Windows sidecar

Accepted as a build strategy, pending native validation. PyInstaller bundles the
interpreter and dependencies in one executable; Tauri bundles that executable using
externalBin. Application source resources are embedded under project/ and imported
at runtime. Collect statically identifiable imports for dynamic route loading.
A prebuilt generic Python runtime is deferred because application dependencies vary.
Developers currently need Rust to build the shell; users of validated final installers
should not. No source installation silently compiles Rust during pip install.
