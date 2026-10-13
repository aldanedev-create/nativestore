# Contributing

Install with `python -m pip install -e ".[dev,packaging]"`. Follow README verification
commands. Add tests for real user behavior and failure cases. Changes to filenames,
route patterns, bridge protocol and CLI behavior need docs and compatibility review.
Keep application logic in Python. Keep frontend capabilities minimal. Run native
launch/exit tests on a platform with Tauri prerequisites when editing the shell.
Do not publish releases from PR workflows. Before submitting, inspect packaged wheels
for accidental caches, build trees, secrets and missing runtime resources.
