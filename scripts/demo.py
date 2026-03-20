#!/usr/bin/env python3
"""Demo script: show all theme presets and README examples with dummy data."""

from __future__ import annotations

import importlib.util
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ── Load main module ────────────────────────────────────────────────────────────
_root = Path(__file__).parent.parent
_spec = importlib.util.spec_from_file_location("claude_nano_line", _root / "claude-nano-line.py")
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

render_custom = _mod.render_custom
render_legacy = _mod.render_legacy
THEMES = _mod.THEMES

# ── Dummy data ──────────────────────────────────────────────────────────────────
_now = datetime.now(timezone.utc)
_five_resets_at = (_now + timedelta(hours=2.5)).isoformat()
_seven_resets_at = (_now + timedelta(days=5)).isoformat()

CTX_REMAINING = 30  # 70% used
USAGE = {
    "five_hour_pct": 42,
    "seven_day_pct": 15,
    "five_resets_at": _five_resets_at,
    "seven_resets_at": _seven_resets_at,
}
MODEL = "claude-sonnet-4-6"
CWD_REAL = "/Users/demo/dev/myproject"
GIT_BRANCH = "feat/awesome"
GIT_DIRTY = True

# ── Helpers ─────────────────────────────────────────────────────────────────────
LABEL_WIDTH = 46
SEP = "│"
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"


def section(title: str) -> None:
    print()
    print(BOLD + "── " + title + " " + "─" * max(0, 60 - len(title)) + RESET)


def row(label: str, output: str) -> None:
    padded = (DIM + label + RESET).ljust(LABEL_WIDTH + len(DIM) + len(RESET))
    print(padded + " " + SEP + " " + output)


# ── Theme presets ───────────────────────────────────────────────────────────────
section("Theme presets  (CLAUDE_NANO_LINE_THEME=<name>)")
for name, fmt in THEMES.items():
    out = render_custom(fmt, CTX_REMAINING, USAGE, MODEL, CWD_REAL, GIT_BRANCH, GIT_DIRTY)
    row(name, out)

# ── Legacy (default) ────────────────────────────────────────────────────────────
section("Legacy (default layout)")
cwd_base = Path(CWD_REAL).name
out = render_legacy(CTX_REMAINING, USAGE, MODEL, cwd_base, GIT_BRANCH, GIT_DIRTY)
row("(no FORMAT/THEME set)", out)

# ── Examples from README ────────────────────────────────────────────────────────
section("Examples  (CLAUDE_NANO_LINE_FORMAT=...)")

EXAMPLES: list[tuple[str, str]] = [
    ("Simple display", "{5h_pct} {7d_pct} {model}"),
    (
        "Custom colors and thresholds",
        "{text:[5h]|color:cyan} {5h_pct|warn-threshold:70,alert-threshold:90} {model}",
    ),
    (
        "Reset time: hours, 2 decimal places",
        "{5h_pct} {text:(}{5h_reset|unit:h,digits:2}{text:)} {model}",
    ),
    (
        "Reset time: days+hours, no decimals",
        "{5h_pct} {text:(}{5h_reset|unit:dh,digits:0}{text:)} {7d_pct} {model}",
    ),
    (
        "Per-model colors",
        "{5h_pct} {model|haiku-color:green,sonnet-color:yellow,opus-color:blue} {cwd}",
    ),
    (
        "With separators",
        "{5h_pct} {text:|} {7d_pct} {text:|} {model} {cwd}",
    ),
    (
        "Reproduce default layout",
        (
            "{text:[ctx]|color:gray} {ctx_pct} "
            "{text:[5h]|color:gray} {5h_pct} "
            "{text:(|color:light_gray}{5h_reset}{text:)|color:light_gray} "
            "{text:[7d]|color:gray} {7d_pct} "
            "{text:(|color:light_gray}{7d_reset}{text:)|color:light_gray} "
            "{model} {cwd|color:bold_yellow}"
            "{text: (|color:cyan}{branch}{text:)|color:cyan}"
        ),
    ),
    (
        "Reset datetime (absolute time)",
        "{5h_pct} {5h_reset_at} {7d_pct} {7d_reset_at} {model}",
    ),
    (
        "Reset datetime with timezone",
        "{5h_pct} {5h_reset_at|format:time_tz} {7d_pct} {7d_reset_at|format:datetime_tz} {model}",
    ),
    (
        "Show in UTC",
        "{5h_reset_at|tz:utc,format:auto_tz} {7d_reset_at|tz:utc,format:full}",
    ),
    (
        "Context token usage (estimated)",
        "{ctx_pct} {ctx_used_tokens}/{ctx_total_tokens} {model}",
    ),
    (
        "Git dirty indicator",
        "{5h_pct} {model} {cwd} {branch_dirty}",
    ),
    (
        "Git dirty with color change",
        "{5h_pct} {model} {cwd} {branch_dirty|color:cyan,dirty-color:yellow}",
    ),
    (
        "Opt-in dirty marker on branch",
        "{5h_pct} {model} {cwd} {branch|dirty-suffix:!,dirty-color:red}",
    ),
]

for label, fmt in EXAMPLES:
    out = render_custom(fmt, CTX_REMAINING, USAGE, MODEL, CWD_REAL, GIT_BRANCH, GIT_DIRTY)
    row("# " + label, out)

print()
