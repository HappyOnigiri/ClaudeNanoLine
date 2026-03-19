# AGENTS.md — Development Guidelines

## README update rule

**README.md and README.ja.md must be kept in sync with the code.**

Whenever a placeholder, option, or feature is added or removed from
`claude-nano-line.py`, update **both** README files before finishing the task:

- **Placeholder table** (`### Placeholder reference` / `### プレースホルダー一覧`): add or
  remove the row for the placeholder.
- **Option table** (`### Option reference` / `### オプション一覧`): add or remove any
  new options (`key`, applies-to, values, default, description).
- **Examples section** (`### Examples` / `### 設定例`): add at least one usage
  example for non-trivial new features.

Treat a README update as part of the same task — do not ship a feature without
it.
