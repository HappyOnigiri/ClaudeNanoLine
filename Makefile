.PHONY: ci install repomix clean lint

REPOMIX_VERSION ?= 1.12.0
CLAUDE_DIR ?= $(HOME)/.claude
DEST_SCRIPT ?= $(CLAUDE_DIR)/claude-nano-line.py
SETTINGS_FILE ?= $(CLAUDE_DIR)/settings.json

STATUS_LINE_ENTRY = {"statusLine":{"type":"command","command":"python3 ~/.claude/claude-nano-line.py"}}

install:
	@mkdir -p "$(CLAUDE_DIR)"
	cp claude-nano-line.py "$(DEST_SCRIPT)"
	chmod +x "$(DEST_SCRIPT)"
	@echo "Installed to $(DEST_SCRIPT)"
	@if [ -f "$(SETTINGS_FILE)" ]; then \
		original=$$(cat "$(SETTINGS_FILE)"); \
	else \
		original="{}"; \
	fi; \
	updated=$$(printf '%s' "$$original" | STATUS_LINE_ENTRY='$(STATUS_LINE_ENTRY)' python3 -c " \
import json, sys, os; \
orig = json.loads(sys.stdin.read()); \
patch = json.loads(os.environ['STATUS_LINE_ENTRY']); \
orig.setdefault('statusLine', {}).update(patch.get('statusLine', {})); \
print(json.dumps(orig, indent=2)) \
"); \
	printf '%s\n' "$$updated" > "$(SETTINGS_FILE)"; \
	echo "Updated $(SETTINGS_FILE)"

ci:
	python3 scripts/ci.py

lint:
	ruff format claude-nano-line.py tests/
	ruff check claude-nano-line.py tests/ --fix
	mdformat --wrap 80 *.md

repomix:
	@mkdir -p tmp/repomix
	npx --yes repomix@$(REPOMIX_VERSION) --quiet -o tmp/repomix/repomix-core.xml

clean:
	rm -rf tmp/
