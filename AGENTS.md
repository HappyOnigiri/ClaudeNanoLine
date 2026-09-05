# AGENTS.md — Development Guide

## Project at a glance

ClaudeNanoLine is a format-string-driven status-line command for Claude Code.
Claude Code invokes it repeatedly, passing one JSON document on stdin. The
script combines that input with Git state and cached Anthropic Usage API data,
renders one ANSI-colored line, and writes it to stdout.

`claude-nano-line.py` is both the implementation and the distributed artifact;
there is no package or build output. Keep it compatible with Python 3.7+ and
stdlib-only at runtime. `certifi` is an optional TLS fallback, not a required
dependency. Failures should degrade to status-line output or an empty value
rather than interrupt Claude Code.

Treat stdout as the status-line protocol: write only the rendered line there,
send diagnostics through `write_log()`, and keep stdin, subprocess, and network
work timeout-bounded.

The main execution path is:

```text
Claude Code stdin JSON -> main() -> Git and usage data -> renderer -> stdout
```

`CLAUDE_NANO_LINE_FORMAT` selects the custom renderer and takes precedence over
`CLAUDE_NANO_LINE_THEME`; without either, the separate default renderer is used.

## Repository map

- `claude-nano-line.py`: production code, built-in themes, and all runtime
  behavior.
- `tests/test_claude_nano_line.py`: unit and integration tests. It loads the
  hyphenated production script with `importlib` as `claude_nano_line` (`cnl`).
- `setup.sh`: remote installer used by the README quick-start command.
- `Makefile` and `scripts/ci.py`: development setup and the local/hosted CI
  entry point.
- `scripts/demo.py`: renders themes and representative formats with fixture data
  for visual inspection.

## Development commands

- `make setup`: create `.venv` and install development tools.
- `make ci`: format and lint the production script and tests, then run the full
  unittest suite. The format and lint steps modify files in place; inspect the
  resulting diff.
- `make demo`: preview default, theme, and custom-format rendering.

Add tests in `tests/test_claude_nano_line.py` alongside the behavior being
changed. Patch attributes on `cnl` for time, filesystem, subprocess, credential,
and network isolation; tests must not use real credentials or make real Usage
API calls.

## Documentation contract

When a change adds, removes, or changes user-facing behavior in
`claude-nano-line.py` or `setup.sh`, update both `README.md` and `README.ja.md`
in the same change. Keep the two files factually equivalent.

- Add or remove placeholders in `Placeholder reference` / `プレースホルダー一覧`.
- Document options in `Option reference` / `オプション一覧`, including the key,
  applicable placeholders, accepted values, default, and behavior.
- Add an example in `Examples` / `設定例` for a non-trivial feature.
- Update setup, requirements, themes, troubleshooting, or other affected
  sections when their documented behavior changes.

## Focused development guides

Read only the guide relevant to the area being changed:

- [`docs/custom-format-rendering.md`](docs/custom-format-rendering.md): custom
  placeholders, options, themes, command tokens, and rendering behavior.
- [`docs/usage-data.md`](docs/usage-data.md): Usage API, credentials, cache,
  error states, and macOS authentication repair.
