# Quickstart

The default starter uses JinjaX + Angular. For its Node.js build steps and optional
lightweight starters, see [developer workflow](developer-workflow.md).

```bash
python -m pip install -e ".[dev,packaging]"
python -m nativestore new my-desk
cd my-desk/frontend
npm ci --ignore-scripts
cd ..
python -m nativestore dev
```

JinjaX-only needs no Node.js: `nativestore new simple-desk --ui minimal`.
Use `--ui htmx-alpine` for a lightweight interactive alternative.

