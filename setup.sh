#!/bin/bash
set -e

SCRIPT_URL="https://raw.githubusercontent.com/HappyOnigiri/ClaudeNanoLine/main/claude-nano-line.py"
CLAUDE_DIR="$HOME/.claude"
DEST_SCRIPT="$CLAUDE_DIR/claude-nano-line.py"
SETTINGS_FILE="$CLAUDE_DIR/settings.json"

STATUS_LINE_ENTRY='{
  "statusLine": {
    "type": "command",
    "command": "python3 ~/.claude/claude-nano-line.py"
  }
}'

# Check dependencies
if ! command -v python3 &>/dev/null; then
  echo "Error: python3 is required but not installed." >&2
  exit 1
fi

# Ensure ~/.claude/ exists
mkdir -p "$CLAUDE_DIR"

# Download claude-nano-line.py
echo "Downloading claude-nano-line.py..."
curl -fsSL "$SCRIPT_URL" -o "$DEST_SCRIPT"
chmod +x "$DEST_SCRIPT"
echo "Saved to $DEST_SCRIPT"

# Merge statusLine into settings.json
if [ -f "$SETTINGS_FILE" ]; then
  original=$(cat "$SETTINGS_FILE")
else
  original="{}"
fi

updated=$(echo "$original" | python3 -c "
import json, sys
orig = json.loads(sys.stdin.read())
patch = json.loads('$STATUS_LINE_ENTRY')
orig.update(patch)
print(json.dumps(orig, indent=2))
")

# Show diff and confirm
echo ""
echo "The following change will be made to $SETTINGS_FILE:"
echo ""
diff <(echo "$original" | python3 -c "import json,sys; print(json.dumps(json.loads(sys.stdin.read()), indent=2))") \
     <(echo "$updated") || true
echo ""

# Read from /dev/tty to support `curl | bash` piped execution
read -r -p "Apply changes? [y/N] " answer </dev/tty
if [[ "$answer" != "y" && "$answer" != "Y" ]]; then
  echo "Aborted."
  exit 0
fi

echo "$updated" > "$SETTINGS_FILE"
echo "Done. $SETTINGS_FILE updated."
