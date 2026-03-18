#!/usr/bin/env python3
"""Claude Code status line - API usage, model, cwd, git branch."""

import json
import os
import re
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

# ── Configuration ──────────────────────────────────────────────────────────────
CACHE_TTL = 360
HTTP_TIMEOUT = 5
DEFAULT_WARN_PCT = 80
DEFAULT_CRIT_PCT = 95
API_URL = "https://api.anthropic.com/api/oauth/usage"
API_USER_AGENT = "ClaudeDesktop/2.0.5"
API_VERSION = "2023-06-01"
API_BETA = "oauth-2025-04-20"

# ── Paths ───────────────────────────────────────────────────────────────────────
CACHE_DIR = Path.home() / ".claude" / "cache"
CACHE_FILE = CACHE_DIR / "claude-usage-cache.json"
LOG_FILE = CACHE_DIR / "claude-usage-api.log"

# ── ANSI Colors ─────────────────────────────────────────────────────────────────
RESET = "\033[0m"
COLOR_MAP = {
    "red": "\033[0;31m",
    "green": "\033[0;32m",
    "yellow": "\033[0;33m",
    "cyan": "\033[0;36m",
    "blue": "\033[1;34m",
    "magenta": "\033[0;35m",
    "gray": "\033[0;37m",
    "light_gray": "\033[38;5;246m",
    "sky_blue": "\033[38;5;117m",
    "pink": "\033[38;5;213m",
    "amber": "\033[38;5;179m",
    "bold": "\033[1m",
    "bold_yellow": "\033[1;33m",
}


# ── Git branch ──────────────────────────────────────────────────────────────────
def get_git_branch(cwd):
    if not cwd:
        return ""
    try:
        env = os.environ.copy()
        env["GIT_OPTIONAL_LOCKS"] = "0"
        result = subprocess.run(
            ["git", "-C", cwd, "symbolic-ref", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
            env=env,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return ""


# ── OAuth token ─────────────────────────────────────────────────────────────────
def get_oauth_token():
    """macOS Keychain -> credentials file の順でトークンを取得"""
    # macOS Keychain
    try:
        result = subprocess.run(
            ["security", "find-generic-password", "-s", "Claude Code-credentials", "-w"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            creds = json.loads(result.stdout.strip())
            return creds["claudeAiOauth"]["accessToken"]
    except Exception:
        pass

    # credentials file (Windows/Linux)
    cred_path = Path.home() / ".claude" / ".credentials.json"
    try:
        with open(cred_path) as f:
            return json.load(f)["claudeAiOauth"]["accessToken"]
    except Exception:
        return None


# ── Cache ───────────────────────────────────────────────────────────────────────
def read_cache():
    """キャッシュを読み、有効なら dict を返す。無効なら None。"""
    try:
        with open(CACHE_FILE) as f:
            d = json.load(f)
        if time.time() - d.get("_ts", 0) < CACHE_TTL:
            return d
    except Exception:
        pass
    return None


def write_cache(data):
    """アトミックにキャッシュ書き込み (tempfile + rename)"""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    data["_ts"] = int(time.time())
    fd, tmp = tempfile.mkstemp(dir=CACHE_DIR, prefix=".claude-usage-", suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f)
        os.replace(tmp, CACHE_FILE)
    except Exception:
        try:
            os.unlink(tmp)
        except Exception:
            pass


def write_log(msg):
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE, "a") as f:
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(ts + " " + msg + "\n")
    except Exception:
        pass


# ── API ─────────────────────────────────────────────────────────────────────────
def to_pct(val):
    if val is None:
        return -1, -1.0
    f = float(val)
    return min(100, int(f)), min(100.0, f)


def fetch_usage(token):
    """Anthropic Usage API を呼び出し、パース済みキャッシュデータを返す"""
    req = Request(
        API_URL,
        headers={
            "Authorization": "Bearer " + token,
            "User-Agent": API_USER_AGENT,
            "anthropic-version": API_VERSION,
            "anthropic-beta": API_BETA,
        },
    )
    try:
        with urlopen(req, timeout=HTTP_TIMEOUT) as resp:
            raw = resp.read()
    except TimeoutError:
        write_log("error:timeout")
        write_cache({"api_error": "timeout"})
        return {"api_error": "timeout"}
    except URLError as e:
        reason = getattr(e, "reason", str(e))
        if "timed out" in str(reason).lower():
            write_log("error:timeout")
            write_cache({"api_error": "timeout"})
            return {"api_error": "timeout"}
        write_log("error:unknown url_error=" + str(reason))
        write_cache({"api_error": "unknown"})
        return {"api_error": "unknown"}
    except HTTPError as e:
        if e.code == 429:
            write_log("error:limit http_status=429")
            write_cache({"api_error": "limit"})
            return {"api_error": "limit"}
        write_log("error:unknown http_status=" + str(e.code))
        write_cache({"api_error": "unknown"})
        return {"api_error": "unknown"}
    except Exception as e:
        write_log("error:unknown exception=" + str(e))
        write_cache({"api_error": "unknown"})
        return {"api_error": "unknown"}

    try:
        d = json.loads(raw)
    except Exception:
        write_log("error:unknown (json parse failed)")
        write_cache({"api_error": "unknown"})
        return {"api_error": "unknown"}

    if "error" in d:
        err_type = d["error"].get("type", "")
        if any(k in err_type for k in ("rate_limit", "usage", "quota")):
            write_log("error:limit type=" + err_type)
            write_cache({"api_error": "limit"})
            return {"api_error": "limit"}
        write_log("error:unknown type=" + err_type)
        write_cache({"api_error": "unknown"})
        return {"api_error": "unknown"}

    five = d.get("five_hour", {})
    seven = d.get("seven_day", {})
    five_pct, five_pct_raw = to_pct(five.get("utilization"))
    seven_pct, seven_pct_raw = to_pct(seven.get("utilization"))
    five_resets_at = five.get("resets_at", "")
    seven_resets_at = seven.get("resets_at", "")

    result = {
        "five_hour_pct": five_pct,
        "five_hour_pct_raw": five_pct_raw,
        "seven_day_pct": seven_pct,
        "seven_day_pct_raw": seven_pct_raw,
        "five_resets_at": five_resets_at,
        "seven_resets_at": seven_resets_at,
    }
    write_log("ok 5h=" + str(five_pct) + "% 7d=" + str(seven_pct) + "%")
    write_cache(result)
    return result


def get_usage_data():
    """キャッシュ確認 -> API 呼び出し -> データを返す"""
    cached = read_cache()
    if cached is not None:
        return cached

    token = get_oauth_token()
    if not token:
        return {}

    return fetch_usage(token)


# ── Rendering helpers ───────────────────────────────────────────────────────────
def fmt_reset_time(iso_str, fmt_type="auto"):
    """ISO 文字列 -> フォーマット済み残り時間"""
    if not iso_str:
        return ""
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        secs = int((dt - datetime.now(timezone.utc)).total_seconds())
        if secs <= 0:
            return ""
        if fmt_type == "hm":
            return str(secs // 3600) + "h" + str((secs % 3600) // 60).zfill(2) + "m"
        elif fmt_type == "h1":
            return "{:.1f}h".format(secs / 3600)
        elif fmt_type == "dh":
            d, rem = divmod(secs, 86400)
            if d > 0:
                return str(d) + "d " + str(rem // 3600) + "h"
            return str(rem // 3600) + "h"
        elif fmt_type == "d1":
            return "{:.1f}d".format(secs / 86400)
        else:  # auto
            if secs < 3600:
                return str(secs // 60) + "m"
            elif secs < 36000:
                return "{:.1f}h".format(secs / 3600)
            elif secs < 86400:
                return str(secs // 3600) + "h" + str((secs % 3600) // 60).zfill(2) + "m"
            else:
                days = secs // 86400
                if days < 2:
                    return str(days) + "d" + str((secs % 86400) // 3600) + "h"
                return str(days) + "d"
    except Exception:
        return ""


def fmt_reset_time_v2(iso_str, unit="auto", digits=1):
    """ISO 文字列 -> unit/digits オプション付きフォーマット済み残り時間"""
    if not iso_str:
        return ""
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        secs = int((dt - datetime.now(timezone.utc)).total_seconds())
        if secs <= 0:
            return ""
        digits = max(0, int(digits))
        fmt = f".{digits}f"
        if unit == "h":
            h = secs / 3600
            return f"{h:{fmt}}h"
        elif unit == "d":
            d = secs / 86400
            return f"{d:{fmt}}d"
        elif unit == "dh":
            d_int, rem = divmod(secs, 86400)
            h = round(rem / 3600, digits)
            if h >= 24:
                d_int += 1
                h = 0.0
            return f"{d_int}d {h:{fmt}}h"
        else:  # auto
            if secs < 3600:
                return str(secs // 60) + "m"
            elif secs < 36000:
                h = secs / 3600
                return f"{h:{fmt}}h"
            elif secs < 86400:
                return str(secs // 3600) + "h" + str((secs % 3600) // 60).zfill(2) + "m"
            else:
                days = secs // 86400
                if days < 2:
                    return str(days) + "d" + str((secs % 86400) // 3600) + "h"
                return f"{days}d"
    except Exception:
        return ""


def colorize(text, color_code):
    if color_code:
        return color_code + text + RESET
    return text


def get_model_color(model_name):
    m = model_name.lower()
    if "haiku" in m:
        return COLOR_MAP["amber"]
    elif "sonnet" in m:
        return COLOR_MAP["sky_blue"]
    elif "opus" in m:
        return COLOR_MAP["pink"]
    return COLOR_MAP["magenta"]


def usage_color(pct, warn_pct=DEFAULT_WARN_PCT, crit_pct=DEFAULT_CRIT_PCT):
    if pct >= crit_pct:
        return COLOR_MAP["red"]
    elif pct >= warn_pct:
        return COLOR_MAP["yellow"]
    return COLOR_MAP["green"]


# ── Legacy rendering ────────────────────────────────────────────────────────────
def render_legacy(ctx_remaining, usage, model, cwd_base, git_branch):
    warn_pct = DEFAULT_WARN_PCT
    crit_pct = DEFAULT_CRIT_PCT
    api_error = usage.get("api_error", "")

    # ctx part
    ctx_part = ""
    if ctx_remaining is not None:
        ctx_used = 100 - int(ctx_remaining)
        ctx_part = (
            colorize("[ctx]", COLOR_MAP["gray"])
            + " "
            + usage_color(ctx_used, warn_pct, crit_pct)
            + str(ctx_used) + "%"
            + RESET
        )

    # usage parts
    five_pct_val = usage.get("five_hour_pct", -1)
    seven_pct_val = usage.get("seven_day_pct", -1)

    if api_error:
        err_map = {
            "limit": "Usage API Rate Limit",
            "timeout": "Timeout",
            "unknown": "Unknown Error",
        }
        five_part = COLOR_MAP["light_gray"] + err_map.get(api_error, "Unknown Error") + RESET
        seven_part = ""
    elif five_pct_val != -1:
        col = usage_color(five_pct_val, warn_pct, crit_pct)
        five_remaining = fmt_reset_time(usage.get("five_resets_at", ""))
        if not five_remaining:
            five_remaining = "5h"
        remaining_str = " " + COLOR_MAP["light_gray"] + "(" + five_remaining + ")" + RESET
        five_part = (
            colorize("[5h]", COLOR_MAP["gray"])
            + " "
            + col
            + str(five_pct_val) + "%"
            + RESET
            + remaining_str
        )

        if seven_pct_val != -1:
            col = usage_color(seven_pct_val, warn_pct, crit_pct)
            seven_remaining = fmt_reset_time(usage.get("seven_resets_at", ""))
            remaining_str = ""
            if seven_remaining:
                remaining_str = (
                    " " + COLOR_MAP["light_gray"] + "(" + seven_remaining + ")" + RESET
                )
            seven_part = (
                colorize("[7d]", COLOR_MAP["gray"])
                + " "
                + col
                + str(seven_pct_val) + "%"
                + RESET
                + remaining_str
            )
        else:
            seven_part = COLOR_MAP["gray"] + "[7d] --%" + RESET
    else:
        five_part = COLOR_MAP["gray"] + "[5h] --%" + RESET
        seven_part = COLOR_MAP["gray"] + "[7d] --%" + RESET

    # model part
    model_part = get_model_color(model) + model + RESET

    # cwd part
    git_info = " (" + git_branch + ")" if git_branch else ""
    cwd_part = (
        COLOR_MAP["bold"]
        + COLOR_MAP["yellow"]
        + cwd_base
        + RESET
        + COLOR_MAP["cyan"]
        + git_info
        + RESET
    )

    # assemble
    line = ctx_part
    usage_line = five_part + (" " + seven_part if seven_part else "")
    line = (line + " " if line else "") + usage_line + " " + model_part + " " + cwd_part
    return line


# ── Custom format rendering ─────────────────────────────────────────────────────
def parse_options(opt_str):
    """カンマ区切りの key:value をパース"""
    opts = {}
    for part in opt_str.split(","):
        if ":" in part:
            k, v = part.split(":", 1)
            opts[k.strip()] = v.strip()
    return opts


def get_threshold_color(pct_val, opts, warn_pct=DEFAULT_WARN_PCT, crit_pct=DEFAULT_CRIT_PCT):
    try:
        warn = int(opts.get("warn-threshold", warn_pct))
    except (TypeError, ValueError):
        warn = warn_pct
    try:
        alert = int(opts.get("alert-threshold", crit_pct))
    except (TypeError, ValueError):
        alert = crit_pct
    c_normal = opts.get("color", "green")
    c_warn = opts.get("warn-color", "yellow")
    c_alert = opts.get("alert-color", "red")
    if pct_val >= alert:
        return COLOR_MAP.get(c_alert, "")
    elif pct_val >= warn:
        return COLOR_MAP.get(c_warn, "")
    else:
        return COLOR_MAP.get(c_normal, "")


def render_custom(fmt, ctx_remaining, usage, model, cwd_real, git_branch):
    api_error = usage.get("api_error", "")
    cwd_short = str(Path(cwd_real)).replace(str(Path.home()), "~") if cwd_real else ""
    cwd_base = Path(cwd_real).name if cwd_real else ""
    if not cwd_base:
        cwd_base = cwd_short

    ctx_used = None
    ctx_used_raw = None
    if ctx_remaining is not None:
        ctx_used = 100 - int(ctx_remaining)
        ctx_used_raw = float(ctx_used)

    def resolve(name, opts):
        # pct 系
        if name in ("ctx_pct", "5h_pct", "7d_pct"):
            prefix_map = {"ctx_pct": "ctx", "5h_pct": "5h", "7d_pct": "7d"}
            prefix = prefix_map[name]

            if api_error and prefix != "ctx":
                err_map = {"limit": "Rate Limit", "timeout": "Timeout"}
                return (
                    err_map.get(api_error, "Error"),
                    COLOR_MAP.get(opts.get("color", "light_gray"), ""),
                )

            if prefix == "ctx":
                int_val = ctx_used
                raw_val = ctx_used_raw
            elif prefix == "5h":
                int_val = usage.get("five_hour_pct", -1)
                raw_val = usage.get("five_hour_pct_raw", -1.0)
            else:  # 7d
                int_val = usage.get("seven_day_pct", -1)
                raw_val = usage.get("seven_day_pct_raw", -1.0)

            if int_val is None or int_val == -1:
                return "--%", COLOR_MAP.get("gray", "")

            pct_int = int(int_val)
            fmt_type = opts.get("format", "pct")
            m = re.match(r"^pct(\d+)$", fmt_type)
            if m:
                n = int(m.group(1))
                if n == 0:
                    val = str(pct_int) + "%"
                elif raw_val is not None and raw_val != -1.0:
                    val = f"{float(raw_val):.{n}f}%"
                else:
                    val = str(pct_int) + "%"
            elif fmt_type == "pct":
                val = str(pct_int) + "%"
            else:
                val = str(pct_int) + "%"

            color = get_threshold_color(pct_int, opts)
            return val, color

        # reset 系
        if name in ("5h_reset", "7d_reset"):
            if name == "5h_reset":
                iso = usage.get("five_resets_at", "")
            else:
                iso = usage.get("seven_resets_at", "")
            unit_opt = opts.get("unit", "")
            digits_opt = opts.get("digits", "")
            if unit_opt or digits_opt:
                unit = unit_opt if unit_opt else "auto"
                try:
                    digits = int(digits_opt) if digits_opt else 1
                except (TypeError, ValueError):
                    digits = 1
                val = fmt_reset_time_v2(iso, unit, digits)
            else:
                fmt_t = opts.get("format", "auto")
                val = fmt_reset_time(iso, fmt_t)
            color = COLOR_MAP.get(opts.get("color", ""), "")
            return val, color

        # model
        if name == "model":
            val = model
            blanket = opts.get("color", "")
            if blanket:
                color = COLOR_MAP.get(blanket, "")
            else:
                m_lower = val.lower()
                per_model_color = ""
                if "haiku" in m_lower:
                    per_model_color = opts.get("haiku-color", "")
                elif "sonnet" in m_lower:
                    per_model_color = opts.get("sonnet-color", "")
                elif "opus" in m_lower:
                    per_model_color = opts.get("opus-color", "")
                color = COLOR_MAP.get(per_model_color, "") if per_model_color else get_model_color(val)
            return val, color

        # cwd 系
        if name == "cwd":
            return cwd_base, COLOR_MAP.get(opts.get("color", ""), "")
        if name == "cwd_short":
            return cwd_short, COLOR_MAP.get(opts.get("color", ""), "")
        if name == "cwd_full":
            return cwd_real or "", COLOR_MAP.get(opts.get("color", ""), "")

        # branch
        if name == "branch":
            return git_branch, COLOR_MAP.get(opts.get("color", ""), "")

        return "", ""

    def process_token(inner):
        if inner.startswith("text:"):
            parts = inner.split("|")
            opts = {}
            text_end = len(parts)
            for i in range(len(parts) - 1, 0, -1):
                parsed = parse_options(parts[i])
                if parsed:
                    opts.update(parsed)
                    text_end = i
                else:
                    break
            text = "|".join(parts[:text_end])[5:]  # 'text:' プレフィクスを除去
            color = COLOR_MAP.get(opts.get("color", ""), "")
            if color:
                return color + text + RESET
            return text

        parts = inner.split("|")
        identifier = parts[0]
        opts = {}
        for p in parts[1:]:
            opts.update(parse_options(p))

        val, color = resolve(identifier, opts)
        if color and val:
            return color + val + RESET
        return val

    return re.sub(r"\{([^}]+)\}", lambda m: process_token(m.group(1)), fmt)


# ── Main ────────────────────────────────────────────────────────────────────────
def main():
    try:
        input_data = json.loads(sys.stdin.read())
    except Exception:
        input_data = {}

    cwd_real = (
        (input_data.get("workspace") or {}).get("current_dir")
        or input_data.get("cwd", "")
        or ""
    )
    model = (input_data.get("model") or {}).get("display_name", "")
    ctx_remaining = (input_data.get("context_window") or {}).get("remaining_percentage")

    git_branch = get_git_branch(cwd_real)
    usage = get_usage_data()

    fmt = os.environ.get("CLAUDE_NANO_LINE_FORMAT", "")
    if fmt:
        output = render_custom(fmt, ctx_remaining, usage, model, cwd_real, git_branch)
    else:
        cwd_short = str(Path(cwd_real)).replace(str(Path.home()), "~") if cwd_real else ""
        cwd_base = Path(cwd_real).name if cwd_real else ""
        if not cwd_base:
            cwd_base = cwd_short
        output = render_legacy(ctx_remaining, usage, model, cwd_base, git_branch)

    print(output, end="")


if __name__ == "__main__":
    main()
