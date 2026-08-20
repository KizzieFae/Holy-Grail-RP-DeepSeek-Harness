# Code Style and Change Scope

This file defines practical coding expectations for AI-assisted edits in this repository.

## Change scope

- Prefer small, reviewable diffs.
- Focus only on files relevant to the request.
- Do not perform broad refactors unless explicitly requested.
- Preserve existing naming, structure, and call patterns where they are already working.
- Reuse existing helpers before adding new ones.

## Python expectations

Follow [v2/README.md](../v2/README.md) and [docs/testing.md](./testing.md) for the primary Python workflow and test commands.

Additional project expectations:

- Keep imports at the top of the file.
- Prefer simple fixes over clever rewrites.
- Avoid duplication when an existing helper or pattern already solves the problem.
- Keep runtime, validation, audit, and prompt concerns in their existing layers.
- When changing public behavior, update or add tests close to the affected area.

## Documentation expectations

- Put important project rules in repo files.
- Update docs when architecture, testing workflow, or audit procedure materially changes.
- Prefer concise, explicit instructions over vague best-practices language.

## Safety expectations

- Do not modify secrets or `.env` files without explicit approval.
- Avoid one-off scripts when a direct code or test change is cleaner.
- Avoid unrelated cleanup in the same change.
