# Custom format rendering

Read this guide when changing placeholders, options, themes, literal text, shell
command tokens, or their rendering tests.

## Rendering paths

`main()` constructs native Claude Code metadata and selects exactly one path:

```text
CLAUDE_NANO_LINE_FORMAT -> render_custom()
CLAUDE_NANO_LINE_THEME  -> THEMES entry -> render_custom()
neither                 -> render_default()
```

The default renderer is independent of the format-string renderer. Decide
explicitly whether a display change belongs in the custom path, the default
path, or both.

Start custom-renderer changes in `render_custom()`: its nested `resolve()`
handles value placeholders and `process_token()` handles token syntax. Unknown
placeholders resolve to an empty string.

Claude Code input is extracted in `main()`; newer session metadata is grouped in
`meta`, while Usage API fields stay in `usage`.

## Parser invariants

- Options are comma-separated `key:value` pairs, and values may contain
  additional colons because `parse_options()` splits only on the first colon.
- Literal text and unquoted commands may contain `|`. Their parsers scan
  option-looking segments from the right so earlier pipes remain content.
- Backtick-wrapped commands use a dedicated token-regex branch and escape-aware
  closing-backtick scan. Changes to command syntax must cover escaped backticks,
  backslashes, pipes, timeouts, and process-group termination.
- `prefix` and `suffix` are applied after a value placeholder resolves and only
  when its value is non-empty. They do not wrap `text:` or `cmd:` tokens.
- Missing data and most runtime failures intentionally become empty or fallback
  display values; keep the renderer safe for repeated status-line invocation.

## Git input invariants

- Detached HEAD falls back from the symbolic branch name to the seven-character
  commit hash.
- Dirty detection intentionally excludes untracked files. Preserve that scope
  unless the user-facing meaning of dirty is deliberately changed.
- Repository identity comes from `workspace.repo` in the Claude Code input. Its
  `get_git_repo_name()` fallback runs at most once per render and only when a
  `repo` placeholder is present, so keep it behind `repo_fields()` instead of
  resolving it eagerly in `main()`.

## Change map

- Placeholder: update `resolve()`, extract/pass any input in `main()`, and cover
  custom rendering plus main integration. Update `render_default()` only when
  the default layout should expose it.
- Option: update the relevant resolver or token branch and cover invalid,
  missing, and boundary values.
- Theme: update `THEMES` and verify every referenced placeholder and option
  through the theme tests and `make demo`.
- Formatting helper: test the helper directly and its dispatch from
  `render_custom()`.

The public placeholder and option contracts live in both README files; follow
the root `AGENTS.md` documentation contract in the same change.
