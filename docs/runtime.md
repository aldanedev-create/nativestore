# Runtime delivery

NativeStore can resolve precompiled desktop/tools executables from platform wheels or
an explicitly supplied trusted release manifest. Every artifact has a version, protocol,
platform key, safe filename and SHA-256. Corrupt or incompatible artifacts fail before
execution. Downloads accept approved HTTPS GitHub release URLs and verified bytes only.
There is no fabricated default release URL or checksum.

Maintainer workflow:

```bash
cargo build -p nativestore-cli --release --locked
cargo build --manifest-path src/nativestore/desktop/Cargo.toml --release --locked
python scripts/stage_native.py --desktop PATH_TO_DESKTOP --tools PATH_TO_CLI
python -m build --wheel
python scripts/verify_distribution.py
```

The staging script hashes actual compiled files. setup.py tags wheels containing native
artifacts as platform wheels with Python-independent py3/none tags. Source distributions
exclude native executables so users do not accidentally build a Linux wheel with Windows
binaries. Normal pip installation does not run cargo.

A trusted manifest can be installed with `nativestore runtime --manifest manifest.json`;
`--offline` requires a verified local/cache artifact. No manifest is downloaded and trusted
from an arbitrary network location. The caller must already trust the supplied manifest.

Windows-native wheel CI is provided. No precompiled desktop executable was produced in
this Linux environment because required native development libraries are absent. Therefore
the current locally built wheel is portable and does not promise desktop startup without
Rust. The native CI artifact is needed to fulfill that developer experience on Windows.
