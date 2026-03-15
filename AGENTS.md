# AGENTS.md

## Cursor Cloud specific instructions

### Overview

ClaudeNanoLine is a single bash script (`claude-nano-line.sh`) that renders a status line for Claude Code. There are no services to start, no build steps, and no package managers. The repository also includes `setup.sh` (an interactive installer).

### Dependencies

System tools: `bash`, `jq`, `python3` (≥3.7), `curl`, `git`. All are pre-installed in the Cloud VM. `shellcheck` may need to be installed for linting (`sudo apt-get install -y shellcheck`).

### Linting

```sh
shellcheck claude-nano-line.sh setup.sh
```

The only expected warning is SC2034 (`BLUE` unused variable) in `claude-nano-line.sh`.

### Running / Testing

The script reads JSON from stdin (the same format Claude Code pipes to statusLine commands). Example:

```sh
echo '{"workspace":{"current_dir":"/workspace"},"model":{"display_name":"Claude Sonnet 4"},"context_window":{"remaining_percentage":72}}' | bash claude-nano-line.sh
```

API usage (`[5h]`/`[7d]`) will show `--%` without a valid Claude Code OAuth token. This is expected in the Cloud VM.

`setup.sh` is interactive (prompts for confirmation) and downloads from GitHub; use `bash -n setup.sh` for syntax validation only.
