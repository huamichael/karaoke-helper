# Test fixtures

Shared recordings and expected lines that every backend task tests against.

- `lines/<name>.json`: one `Line` object, the expected syllables.
- `audio/<name>__<variant>.wav`: a 16 kHz mono recording of that line.

Naming rules and variants: `docs/contracts/backend-interfaces.md`, section 6. Keeper: D.
