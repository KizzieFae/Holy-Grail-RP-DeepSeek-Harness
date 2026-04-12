# Testing Expectations

Before changing Python code, read:

- `docs/testing.md`
- `python/README.md`

Follow these expectations:

- run the smallest relevant tests first
- run broader checks when shared infrastructure or architecture-sensitive paths are affected
- add or update focused tests when public behavior or important runtime behavior changes
- use `pytest`, fixtures, and mocks according to existing repo practice
- avoid real external-service calls in tests when mocks or replay clients are appropriate

For RP app work, treat audit reruns as verification support, not as a substitute for regression tests.
