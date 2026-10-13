# Release policy

0.1.0 is the normal release version. Native platform checks gate publication. Track implemented and validated
features separately. Protocol 1 changes require compatibility tests or a new protocol.
Before stable release, pin supported native dependencies, build platform wheels with
prebuilt CLI/runtime artifacts, run clean Windows install/launch/exit tests, audit
third-party licenses/dependencies, sign installers and establish a vulnerability contact.

Release CI builds wheels/sdists and validates them before PyPI trusted publishing.
Publishing is manually triggered, uses a protected pypi environment, and requires
repository/PyPI trusted publisher configuration. No tokens belong in source.
