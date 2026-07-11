#!/usr/bin/env python3
# Copyright (c) 2026 HappyOnigiri
# MIT License
# https://github.com/HappyOnigiri/ClaudeNanoLine
#
# Usage: set as Claude Code statusLine command in ~/.claude/settings.json:
#   "statusLine": {"type": "command", "command": "python3 ~/.claude/claude-nano-line.py"}
# Customize output via CLAUDE_NANO_LINE_FORMAT environment variable.
"""Claude Code status line - API usage, model, cwd, git branch."""

from __future__ import annotations

__version__ = "1.5.0"

import hashlib
import json
import os
import queue
import re
import signal
import ssl
import subprocess
import sys
import tempfile
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

try:
    import certifi  # optional; used as CA bundle fallback when Python's default trust store is unusable
except ImportError:  # pragma: no cover
    certifi = None

# ── Configuration ──────────────────────────────────────────────────────────────
CACHE_TTL = 360
HTTP_TIMEOUT = 5
GLOBAL_TIMEOUT = 20
STDIN_TIMEOUT = 3
CMD_TIMEOUT = 2
DEFAULT_WARN_PCT = 80
DEFAULT_CRIT_PCT = 95
API_URL = "https://api.anthropic.com/api/oauth/usage"
AUTO_FIX_AUTH_COOLDOWN = 3600  # 認証修復コマンドの再実行を抑止する最短間隔（秒）= 1時間
AUTH_STUCK_GRACE = 3600  # トークン期限切れがこの秒数を超えたら「更新が詰まっている」とみなす

MODEL_CONTEXT_SIZES = {
    "1m context": 1_000_000,
    "opus": 200_000,
    "sonnet": 200_000,
    "haiku": 200_000,
}
DEFAULT_CONTEXT_SIZE = 200_000
API_USER_AGENT = "ClaudeDesktop/2.0.5"
API_VERSION = "2023-06-01"
API_BETA = "oauth-2025-04-20"


# ── Paths ───────────────────────────────────────────────────────────────────────
def _resolve_xdg_dir(env_name: str, fallback: Path) -> Path:
    value = os.environ.get(env_name)
    if value and Path(value).is_absolute():
        return Path(value)
    return fallback


os.environ.setdefault("GIT_OPTIONAL_LOCKS", "0")

_xdg_cache = _resolve_xdg_dir("XDG_CACHE_HOME", Path.home() / ".cache")
_xdg_state = _resolve_xdg_dir("XDG_STATE_HOME", Path.home() / ".local" / "state")
CACHE_DIR = _xdg_cache / "claude-nano-line"
CACHE_FILE = CACHE_DIR / "claude-usage-cache.json"
LOG_DIR = _xdg_state / "claude-nano-line"
LOG_FILE = LOG_DIR / "claude-usage-api.log"

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
    "purple": "\033[38;5;141m",
    "bold": "\033[1m",
    "bold_yellow": "\033[1;33m",
}

EFFORT_DEFAULT_COLORS = {
    "low": "yellow",
    "medium": "green",
    "high": "sky_blue",
    "xhigh": "purple",
    "max": "red",
}

THEMES = {
    "classic": (
        "{text:[ctx]|color:gray} {ctx_pct} "
        "{text:[5h]|color:gray} {5h_pct} {text:(|color:light_gray}{5h_reset|color:light_gray}{text:)|color:light_gray} "
        "{text:[7d]|color:gray} {7d_pct} {text:(|color:light_gray}{7d_reset|color:light_gray}{text:)|color:light_gray} "
        "{model} {cwd|color:bold_yellow}{text: (|color:cyan}{branch_dirty|color:cyan}{text:)|color:cyan}"
    ),
    "minimal": ("{ctx_pct|color:cyan} {5h_pct} {model|color:light_gray} {cwd_short|color:gray}"),
    "ocean": (
        "{text:ctx |color:sky_blue}{ctx_pct|color:sky_blue,warn-color:yellow,alert-color:red} "
        "{text:5h |color:cyan}{5h_pct|color:cyan,warn-color:yellow,alert-color:red} "
        "{text:7d |color:blue}{7d_pct|color:blue,warn-color:yellow,alert-color:red} "
        "{model|haiku-color:cyan,sonnet-color:sky_blue,opus-color:blue} "
        "{cwd|color:sky_blue} {branch_dirty|color:cyan}"
    ),
    "forest": (
        "{ctx_pct|color:green,warn-color:yellow,alert-color:red} "
        "{text:5h|color:green} {5h_pct|color:green,warn-color:yellow,alert-color:red} "
        "{text:7d|color:green} {7d_pct|color:green,warn-color:yellow,alert-color:red} "
        "{model|haiku-color:green,sonnet-color:cyan,opus-color:magenta} "
        "{cwd|color:green} {branch_dirty|color:cyan,dirty-color:yellow}"
    ),
    "sunset": (
        "{ctx_pct|color:amber,warn-color:yellow,alert-color:red} "
        "{text:5h|color:amber} {5h_pct|color:amber,warn-color:yellow,alert-color:red} "
        "{text:7d|color:amber} {7d_pct|color:amber,warn-color:yellow,alert-color:red} "
        "{model|haiku-color:amber,sonnet-color:pink,opus-color:magenta} "
        "{cwd|color:amber} {branch_dirty|color:pink,dirty-color:red}"
    ),
    "nerd": (
        "{ctx_pct} {ctx_used_tokens}/{ctx_total_tokens} "
        "{text:5h|color:gray} {5h_pct} {5h_reset|color:light_gray} "
        "{text:7d|color:gray} {7d_pct} {7d_reset|color:light_gray} "
        "{model|haiku-color:amber,sonnet-color:sky_blue,opus-color:pink} "
        "{cwd_short|color:bold_yellow} {branch_dirty|color:cyan,dirty-color:red}"
    ),
    # Cool segment-priming baseline tuned for low-distraction glanceability:
    # ctx → sky_blue, 5h → cyan, 7d → green map to "cognitive distance" (now / near / far)
    # so each percentage is pre-attentively distinguishable without reading the label.
    # Identity colors mirror Claude Code's native dark-ansi chrome (model pink for opus,
    # path bold_yellow, branch cyan) so the line harmonizes with the host UI instead of
    # competing with it. Yellow/red are reserved for warn/alert thresholds — when the
    # baseline is uniformly cool, a single warm segment is pre-attentive.
    "harmony": (
        "{ctx_pct|color:sky_blue,warn-color:yellow,alert-color:red} "
        "{ctx_used_tokens|color:light_gray}/{ctx_total_tokens|color:light_gray} "
        "{text:5h|color:gray} {5h_pct|color:cyan,warn-color:yellow,alert-color:red} "
        "{5h_reset|color:light_gray} "
        "{text:7d|color:gray} {7d_pct|color:green,warn-color:yellow,alert-color:red} "
        "{7d_reset|color:light_gray} "
        "{model|haiku-color:amber,sonnet-color:sky_blue,opus-color:pink} "
        "{cwd_short|color:bold_yellow} {branch_dirty|color:cyan,dirty-color:amber} "
        # Right side: native Claude Code session metadata picked for ADHD time-blindness
        # support (duration), concrete progress feedback (lines_added/removed), and
        # consequence awareness (cost). Hidden when zero/default to avoid ambient noise.
        "{lines_added|color:cyan,hide-zero:1} "
        "{lines_removed|color:light_gray,hide-zero:1} "
        "{duration|color:light_gray,hide-under-sec:60} "
        "{cost|color:light_gray,hide-zero:1} "
        "{effort|color:pink,hide-if:medium}"
    ),
}


# ── Git branch ──────────────────────────────────────────────────────────────────
def get_git_branch(cwd):
    if not cwd:
        return ""
    try:
        result = subprocess.run(
            ["git", "-C", cwd, "symbolic-ref", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return ""


# ── Git dirty ───────────────────────────────────────────────────────────────────
def get_git_dirty(cwd):
    if not cwd:
        return False
    try:
        result = subprocess.run(
            ["git", "-C", cwd, "status", "--porcelain", "--untracked-files=no"],
            capture_output=True,
            text=True,
            timeout=3,
        )
        if result.returncode == 0:
            return bool(result.stdout.strip())
    except Exception:
        pass
    return False


# ── Git commit (detached HEAD fallback) ─────────────────────────────────────────
def get_git_commit(cwd):
    if not cwd:
        return ""
    try:
        result = subprocess.run(
            ["git", "-C", cwd, "rev-parse", "--short=7", "HEAD"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return ""


# ── OAuth token ─────────────────────────────────────────────────────────────────
def _extract_token(oauth_data):
    """claudeAiOauth dict からトークンを取り出し、期限切れなら warn ログを出す。

    Returns:
        accessToken (str) or None
    """
    token = oauth_data.get("accessToken")
    if not token:
        return None
    expires_at = oauth_data.get("expiresAt")
    if expires_at is not None:
        try:
            expires_epoch = int(expires_at) / 1000  # ms -> sec
            if time.time() >= expires_epoch:
                write_log("warn:token expired (run /login in Claude Code)")
                return None
        except (ValueError, TypeError):
            pass
    return token


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
            return _extract_token(creds.get("claudeAiOauth", {}))
    except Exception:
        pass

    # credentials file (Windows/Linux)
    cred_path = Path.home() / ".claude" / ".credentials.json"
    try:
        with open(cred_path) as f:
            return _extract_token(json.load(f).get("claudeAiOauth", {}))
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
    data["_ts"] = time.time()
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
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        with open(LOG_FILE, "a") as f:
            ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            f.write(ts + " " + msg + "\n")
    except Exception:
        pass


# ── Auth auto-fix (macOS, opt-in) ───────────────────────────────────────────────
def _auth_fix_marker_path() -> Path:
    """認証修復コマンドの最終実行時刻を記録するマーカーのパス。

    LOG_DIR を呼び出し時に参照するため、LOG_DIR を差し替える既存テストで
    自動的に隔離される（モジュール定数にしない理由）。
    """
    return LOG_DIR / "auth-fix.marker"


def _auto_fix_enabled() -> bool:
    """環境変数 CLAUDE_NANO_LINE_AUTO_FIX_AUTH が truthy なら True（既定 OFF）"""
    val = os.environ.get("CLAUDE_NANO_LINE_AUTO_FIX_AUTH", "")
    return val.strip().lower() in ("1", "true", "yes", "on")


def _auth_fix_on_cooldown() -> bool:
    """マーカーの記録時刻からクールダウン期間内なら True（連打防止）"""
    try:
        last = float(_auth_fix_marker_path().read_text().strip())
        return time.time() - last < AUTO_FIX_AUTH_COOLDOWN
    except Exception:
        return False


def _clear_auth_fix_marker() -> None:
    """マーカーを削除する（認証回復時に呼び、次の障害エピソードで再び効くようにする）"""
    try:
        _auth_fix_marker_path().unlink()
    except Exception:
        pass


def _keychain_auth_stuck() -> bool:
    """Keychain にトークンはあるが期限切れが grace 超で継続しているか（Scenario B）"""
    if sys.platform != "darwin":
        return False
    try:
        result = subprocess.run(
            ["security", "find-generic-password", "-s", "Claude Code-credentials", "-w"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            return False
        oauth = json.loads(result.stdout.strip()).get("claudeAiOauth", {})
        expires_at = oauth.get("expiresAt")
        if expires_at is None:
            return False
        return time.time() - int(expires_at) / 1000 > AUTH_STUCK_GRACE
    except Exception:
        return False


def maybe_fix_keychain_auth(reason: str) -> None:
    """確定した認証障害を検知したとき、macOS Keychain の認証エントリを削除する。

    opt-in (CLAUDE_NANO_LINE_AUTO_FIX_AUTH) かつ macOS 限定。クールダウン中は
    スキップ。marker を先に書いてから実行することで、コマンドが途中失敗・ハング
    しても再実行を AUTO_FIX_AUTH_COOLDOWN 秒間抑止する。
    """
    try:
        if not _auto_fix_enabled():
            return
        if sys.platform != "darwin":
            return
        if _auth_fix_on_cooldown():
            return
        LOG_DIR.mkdir(parents=True, exist_ok=True)
        _auth_fix_marker_path().write_text(str(time.time()))
        result = subprocess.run(
            ["security", "delete-generic-password", "-s", "Claude Code-credentials"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        write_log("info:auth-fix attempted reason=" + reason + " rc=" + str(result.returncode))
    except subprocess.TimeoutExpired:
        write_log("info:auth-fix timeout reason=" + reason)
    except Exception as e:
        write_log("info:auth-fix error=" + str(e))


# ── SSL ─────────────────────────────────────────────────────────────────────────
def _build_ssl_context():
    """HTTPS 用 SSL コンテキストを構築する。

    既定の CA ストアが壊れている (python.org 版 Python で
    Install Certificates.command 未実行など) 環境では、
    certifi が import できればそちらの CA バンドルを読み込む。
    どちらも無い場合は create_default_context() の結果をそのまま返し、
    失敗時の URLError を fetch_usage 側でログする。
    """
    ctx = ssl.create_default_context()

    # ssl モジュールが参照する既定 CA が実在するか確認
    paths = ssl.get_default_verify_paths()
    default_ok = bool(paths.cafile) or (paths.capath and os.path.isdir(paths.capath))
    if default_ok:
        return ctx

    if certifi is not None:
        try:
            ctx.load_verify_locations(cafile=certifi.where())
        except Exception:
            pass
    return ctx


_SSL_CONTEXT = _build_ssl_context()


# ── API ─────────────────────────────────────────────────────────────────────────
def _token_hash(token):
    """トークンの先頭8文字のSHA256（ログに生トークンを残さないための短縮ハッシュ）"""
    return hashlib.sha256(token.encode()).hexdigest()[:8]


def to_pct(val):
    if val is None:
        return -1
    return min(100, int(float(val)))


def fetch_usage(token, force_auth_retry=False):
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
        with urlopen(req, timeout=HTTP_TIMEOUT, context=_SSL_CONTEXT) as resp:
            raw = resp.read()
    except TimeoutError:
        write_log("error:timeout")
        write_cache({"api_error": "timeout"})
        return {"api_error": "timeout"}
    except HTTPError as e:
        if e.code == 401:
            write_log("error:auth http_status=401")
            write_cache(
                {
                    "api_error": "auth",
                    "_token_hash": _token_hash(token),
                    "_auth_retry_done": force_auth_retry,
                }
            )
            if force_auth_retry:
                maybe_fix_keychain_auth("http401")
            return {"api_error": "auth"}
        if e.code == 429:
            write_log("error:limit http_status=429")
            write_cache({"api_error": "limit"})
            return {"api_error": "limit"}
        write_log("error:unknown http_status=" + str(e.code))
        write_cache({"api_error": "unknown"})
        return {"api_error": "unknown"}
    except URLError as e:
        reason = getattr(e, "reason", str(e))
        if "timed out" in str(reason).lower():
            write_log("error:timeout")
            write_cache({"api_error": "timeout"})
            return {"api_error": "timeout"}
        if isinstance(reason, ssl.SSLError):
            write_log("error:ssl reason=" + str(reason))
            write_cache({"api_error": "unknown"})
            return {"api_error": "unknown"}
        if "unauthorized" in str(reason).lower():
            write_log("error:auth url_error=" + str(reason))
            write_cache(
                {
                    "api_error": "auth",
                    "_token_hash": _token_hash(token),
                    "_auth_retry_done": force_auth_retry,
                }
            )
            if force_auth_retry:
                maybe_fix_keychain_auth("urlerror-unauthorized")
            return {"api_error": "auth"}
        write_log("error:unknown url_error=" + str(reason))
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
    five_pct = to_pct(five.get("utilization"))
    seven_pct = to_pct(seven.get("utilization"))
    five_resets_at = five.get("resets_at", "")
    seven_resets_at = seven.get("resets_at", "")

    result = {
        "five_hour_pct": five_pct,
        "seven_day_pct": seven_pct,
        "five_resets_at": five_resets_at,
        "seven_resets_at": seven_resets_at,
    }
    write_log("ok 5h=" + str(five_pct) + "% 7d=" + str(seven_pct) + "%")
    write_cache(result)
    _clear_auth_fix_marker()
    return result


def _fetch_with_auto_fix(token):
    """トークンを使ってAPIを呼び出す。401エラーの場合、opt-in設定が有効なら
    同一プロセス内で検証のための強制リトライ -> Keychain自動修復 -> 別のトークンで再試行を試みる。
    """
    res = fetch_usage(token)
    if res.get("api_error") == "auth" and _auto_fix_enabled():
        # 1回目の401発生後、一時的なエラーか検証するために、同一トークンで1回だけ即時再試行
        write_log("info:auth error; verifying with instant retry")
        res2 = fetch_usage(token, force_auth_retry=True)
        if res2.get("api_error") == "auth":
            # 2回連続で401エラーとなり、Keychain削除が実行されたはずなので、
            # 新しいトークン（credentials file 等の別ソース）の取得を試みる
            new_token = get_oauth_token()
            if new_token and _token_hash(new_token) != _token_hash(token):
                write_log("info:keychain auth cleared; retrying with credentials file token")
                return fetch_usage(new_token)
        else:
            return res2
    return res


def _is_reset_since(iso_str, cached_ts):
    """キャッシュ取得時刻から現在までの間にリセット時刻を跨いだか判定"""
    if not iso_str:
        return False
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        reset_epoch = dt.timestamp()
        return cached_ts <= reset_epoch <= time.time()
    except Exception:
        return False


def get_usage_data():
    """キャッシュ確認 -> API 呼び出し -> データを返す"""
    cached = read_cache()
    if cached is not None:
        cached_err = cached.get("api_error", "")
        # auth error キャッシュ中でも、Keychainのトークンが変わっていたら即時再試行
        if cached_err in ("unknown", "auth"):
            token = get_oauth_token()
            cached_hash = cached.get("_token_hash")
            if token and cached_hash and _token_hash(token) != cached_hash:
                write_log("info:token changed; bypassing auth error cache")
                return _fetch_with_auto_fix(token)
            # トークンが取得できるのにhashがない場合 = no-token状態から復帰した（auth限定）
            if token and cached_err == "auth" and not cached_hash:
                write_log("info:token now available; bypassing no-token auth error cache")
                return _fetch_with_auto_fix(token)
            # トークンが同じでも、認証エラー時は1回だけ強制再試行する
            if token and cached_hash and not cached.get("_auth_retry_done", False):
                write_log("info:forcing one auth retry with current token")
                write_cache({**cached, "_auth_retry_done": True})
                res = fetch_usage(token, force_auth_retry=True)
                if res.get("api_error") == "auth" and _auto_fix_enabled():
                    new_token = get_oauth_token()
                    if new_token and _token_hash(new_token) != _token_hash(token):
                        write_log("info:keychain auth cleared; retrying with credentials file token")
                        return fetch_usage(new_token)
                return res
        ts = cached.get("_ts", 0)
        if _is_reset_since(cached.get("five_resets_at"), ts):
            cached["five_hour_pct"] = 0
        if _is_reset_since(cached.get("seven_resets_at"), ts):
            cached["seven_day_pct"] = 0
        return cached

    token = get_oauth_token()
    if not token:
        write_log("warn:no token (expired or missing — run /login in Claude Code)")
        write_cache({"api_error": "auth"})
        if _auto_fix_enabled() and _keychain_auth_stuck():
            maybe_fix_keychain_auth("token-stuck-expired")
            new_token = get_oauth_token()
            if new_token:
                write_log("info:keychain auth stuck-expired fixed; retrying with credentials file token")
                return _fetch_with_auto_fix(new_token)
        return {"api_error": "auth"}

    return _fetch_with_auto_fix(token)


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
            elif secs < 90000:
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
            elif secs < 90000:
                return str(secs // 3600) + "h" + str((secs % 3600) // 60).zfill(2) + "m"
            else:
                days = secs // 86400
                if days < 2:
                    return str(days) + "d" + str((secs % 86400) // 3600) + "h"
                return f"{days}d"
    except Exception:
        return ""


def fmt_reset_datetime(iso_str, fmt_type="auto", tz_local=True):
    """ISO 文字列 -> フォーマット済みリセット日時"""
    if not iso_str:
        return ""
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        if tz_local:
            dt = dt.astimezone()
            now = datetime.now().astimezone()
        else:
            dt = dt.astimezone(timezone.utc)
            now = datetime.now(timezone.utc)

        # _tz サフィックスの判定・除去
        show_tz = fmt_type.endswith("_tz")
        base_fmt = fmt_type[:-3] if show_tz else fmt_type
        tz_suffix = " " + dt.strftime("%Z") if show_tz else ""

        if base_fmt == "time":
            return dt.strftime("%H:%M") + tz_suffix
        elif base_fmt == "datetime":
            return f"{dt.month}/{dt.day:02d} {dt.strftime('%H:%M')}" + tz_suffix
        elif base_fmt == "full":
            return dt.strftime("%Y-%m-%d %H:%M") + tz_suffix
        elif base_fmt == "iso":
            return dt.isoformat()
        else:  # auto
            if dt.date() == now.date():
                return dt.strftime("%H:%M") + tz_suffix
            else:
                return f"{dt.month}/{dt.day:02d} {dt.strftime('%H:%M')}" + tz_suffix
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


def fmt_tokens(count):
    """トークン数を 150k / 1.2M のように短縮表示"""
    if count is None:
        return "--"
    count = int(count)
    if count >= 1_000_000:
        return "{:.1f}M".format(count / 1_000_000)
    if count >= 1_000:
        return "{}k".format(count // 1000)
    return str(count)


def fmt_duration_ms(ms):
    """ミリ秒を 47s / 12m / 1h23m のように短縮表示"""
    if ms is None:
        return ""
    try:
        secs = int(ms) // 1000
    except (TypeError, ValueError):
        return ""
    if secs < 60:
        return "{}s".format(secs)
    mins = secs // 60
    if mins < 60:
        return "{}m".format(mins)
    hours, rem_min = divmod(mins, 60)
    if rem_min == 0:
        return "{}h".format(hours)
    return "{}h{}m".format(hours, rem_min)


def fmt_cost(usd, digits=2):
    """USD コストを $0.42 形式で表示"""
    if usd is None:
        return ""
    try:
        v = float(usd)
    except (TypeError, ValueError):
        return ""
    return "${:.{d}f}".format(v, d=digits)


def estimate_tokens(model_name, ctx_remaining_pct, context_window=None):
    """context_window の実測値を優先し、無ければモデル名と remaining_percentage から推定

    Claude Code は statusline 入力 JSON の context_window に実測値
    (context_window_size / total_input_tokens) を渡してくる。実測値があれば
    それをそのまま使い、無い場合のみ従来のモデル名推定にフォールバックする。
    モデル名推定は表示名に依存するため、"1m context" を含まない 1M モデル
    (例: Fable 5) で誤って 200k と表示される問題があった。
    """
    if ctx_remaining_pct is None:
        return None, None
    cw = context_window or {}
    total = cw.get("context_window_size")
    if not total:
        m = model_name.lower()
        total = DEFAULT_CONTEXT_SIZE
        for key, size in MODEL_CONTEXT_SIZES.items():
            if key in m:
                total = size
                break
    used = cw.get("total_input_tokens")
    if used is None:
        used = int(total * (100 - int(ctx_remaining_pct)) / 100)
    return used, total


# ── Default rendering ────────────────────────────────────────────────────────────
def render_default(ctx_remaining, usage, model, cwd_base, git_branch, git_dirty=False):
    warn_pct = DEFAULT_WARN_PCT
    crit_pct = DEFAULT_CRIT_PCT
    api_error = usage.get("api_error", "")

    # ctx part
    ctx_part = ""
    if ctx_remaining is not None:
        ctx_used = 100 - int(ctx_remaining)
        ctx_pct_str = str(ctx_used) + "%"
        ctx_part = (
            colorize("[ctx]", COLOR_MAP["gray"]) + " " + usage_color(ctx_used, warn_pct, crit_pct) + ctx_pct_str + RESET
        )

    # usage parts
    five_pct_val = usage.get("five_hour_pct", -1)
    seven_pct_val = usage.get("seven_day_pct", -1)

    if api_error:
        err_map = {
            "auth": "Token Expired (/login)",
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
        five_part = colorize("[5h]", COLOR_MAP["gray"]) + " " + col + str(five_pct_val) + "%" + RESET + remaining_str

        if seven_pct_val != -1:
            col = usage_color(seven_pct_val, warn_pct, crit_pct)
            seven_remaining = fmt_reset_time(usage.get("seven_resets_at", ""))
            remaining_str = ""
            if seven_remaining:
                remaining_str = " " + COLOR_MAP["light_gray"] + "(" + seven_remaining + ")" + RESET
            seven_part = (
                colorize("[7d]", COLOR_MAP["gray"]) + " " + col + str(seven_pct_val) + "%" + RESET + remaining_str
            )
        else:
            seven_part = COLOR_MAP["gray"] + "[7d] --%" + RESET
    else:
        five_part = COLOR_MAP["gray"] + "[5h] --%" + RESET
        seven_part = COLOR_MAP["gray"] + "[7d] --%" + RESET

    # model part
    model_part = get_model_color(model) + model + RESET

    # cwd part
    dirty_mark = "*" if git_dirty else ""
    git_info = " (" + git_branch + dirty_mark + ")" if git_branch else ""
    cwd_part = COLOR_MAP["bold"] + COLOR_MAP["yellow"] + cwd_base + RESET + COLOR_MAP["cyan"] + git_info + RESET

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


def _resolve_on_error(opts):
    raw = opts.get("on-error", "")
    if not raw:
        return "default", ""
    if raw == "hide":
        return "hide", ""
    m = re.match(r"^text\((.+)\)$", raw)
    if m:
        return "text", m.group(1)
    return "default", ""


def render_custom(fmt, ctx_remaining, usage, model, cwd_real, git_branch, git_dirty=False, meta=None):
    api_error = usage.get("api_error", "")
    cwd_short = str(Path(cwd_real)).replace(str(Path.home()), "~") if cwd_real else ""
    cwd_base = Path(cwd_real).name if cwd_real else ""
    if not cwd_base:
        cwd_base = cwd_short

    ctx_used = None
    if ctx_remaining is not None:
        ctx_used = 100 - int(ctx_remaining)

    meta = meta or {}

    def resolve(name, opts):
        # pct 系
        if name in ("ctx_pct", "5h_pct", "7d_pct"):
            prefix_map = {"ctx_pct": "ctx", "5h_pct": "5h", "7d_pct": "7d"}
            prefix = prefix_map[name]

            if api_error and prefix != "ctx":
                mode, custom_text = _resolve_on_error(opts)
                if mode == "hide":
                    return "", ""
                if mode == "text":
                    return custom_text, COLOR_MAP.get(opts.get("color", "light_gray"), "")
                err_map = {"auth": "/login", "limit": "Rate Limit", "timeout": "Timeout", "unknown": "Unknown"}
                return err_map.get(api_error, "Unknown"), COLOR_MAP.get(opts.get("color", "light_gray"), "")

            if prefix == "ctx":
                int_val = ctx_used
            elif prefix == "5h":
                int_val = usage.get("five_hour_pct", -1)
            else:  # 7d
                int_val = usage.get("seven_day_pct", -1)

            hide_under_raw = opts.get("hide-under", "")
            hide_under_n = None
            if hide_under_raw:
                try:
                    hide_under_n = int(hide_under_raw)
                except (ValueError, TypeError):
                    pass

            if int_val is None or int_val == -1:
                if hide_under_n is not None:
                    return "", ""
                return "--%", COLOR_MAP.get("gray", "")

            pct_int = int(int_val)

            if hide_under_n is not None and pct_int < hide_under_n:
                return "", ""

            val = str(pct_int) + "%"

            color = get_threshold_color(pct_int, opts)
            return val, color

        # reset 系
        if name in ("5h_reset", "7d_reset"):
            if api_error:
                mode, custom_text = _resolve_on_error(opts)
                if mode == "hide":
                    return "", ""
                if mode == "text":
                    return custom_text, COLOR_MAP.get(opts.get("color", ""), "")
                err_map = {"auth": "/login", "limit": "Rate Limit", "timeout": "Timeout", "unknown": "Unknown"}
                return err_map.get(api_error, "Unknown"), COLOR_MAP.get(opts.get("color", ""), "")
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

        if name in ("5h_reset_at", "7d_reset_at"):
            if api_error:
                mode, custom_text = _resolve_on_error(opts)
                if mode == "hide":
                    return "", ""
                if mode == "text":
                    return custom_text, COLOR_MAP.get(opts.get("color", ""), "")
                err_map = {"auth": "/login", "limit": "Rate Limit", "timeout": "Timeout", "unknown": "Unknown"}
                return err_map.get(api_error, "Unknown"), COLOR_MAP.get(opts.get("color", ""), "")
            if name == "5h_reset_at":
                iso = usage.get("five_resets_at", "")
            else:
                iso = usage.get("seven_resets_at", "")
            fmt_t = opts.get("format", "auto")
            tz_local = opts.get("tz", "local") != "utc"
            val = fmt_reset_datetime(iso, fmt_t, tz_local)
            color = COLOR_MAP.get(opts.get("color", ""), "")
            return val, color

        # model
        if name == "model":
            val = model
            if opts.get("hide-if", "") == val:
                return "", ""
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
            val = cwd_base
            if opts.get("hide-if", "") == val:
                return "", ""
            return val, COLOR_MAP.get(opts.get("color", ""), "")
        if name == "cwd_short":
            val = cwd_short
            if opts.get("hide-if", "") == val:
                return "", ""
            return val, COLOR_MAP.get(opts.get("color", ""), "")
        if name == "cwd_full":
            val = cwd_real or ""
            if opts.get("hide-if", "") == val:
                return "", ""
            return val, COLOR_MAP.get(opts.get("color", ""), "")

        # branch
        if name == "branch":
            if opts.get("hide-if", "") == git_branch:
                return "", ""
            suffix = opts.get("dirty-suffix", "")
            if suffix and git_dirty:
                dc = opts.get("dirty-color", "")
                color_code = COLOR_MAP.get(dc, "") if dc else COLOR_MAP.get(opts.get("color", ""), "")
                return git_branch + suffix, color_code
            return git_branch, COLOR_MAP.get(opts.get("color", ""), "")

        if name == "branch_dirty":
            if opts.get("hide-if", "") == git_branch:
                return "", ""
            suffix = opts.get("dirty-suffix", "*")
            if git_dirty:
                dc = opts.get("dirty-color", "")
                color_code = COLOR_MAP.get(dc, "") if dc else COLOR_MAP.get(opts.get("color", ""), "")
                return git_branch + suffix, color_code
            return git_branch, COLOR_MAP.get(opts.get("color", ""), "")

        if name in ("ctx_tokens", "ctx_used_tokens", "ctx_total_tokens"):
            used, total = estimate_tokens(model, ctx_remaining, meta.get("context_window"))
            if name == "ctx_tokens":
                raw = (total - used) if used is not None else None
            elif name == "ctx_used_tokens":
                raw = used
            else:  # ctx_total_tokens
                raw = total if used is not None else None
            val = fmt_tokens(raw)
            if ctx_used is not None:
                color = get_threshold_color(ctx_used, opts)
            else:
                color = COLOR_MAP.get(opts.get("color", "gray"), "")
            return val, color

        # Native Claude Code session metadata
        if name in ("duration", "api_duration"):
            ms = meta.get("duration_ms" if name == "duration" else "api_duration_ms")
            if ms is None:
                return "", ""
            try:
                hide_under = int(opts.get("hide-under-sec", "0"))
            except (TypeError, ValueError):
                hide_under = 0
            if hide_under and (int(ms) // 1000) < hide_under:
                return "", ""
            val = fmt_duration_ms(ms)
            if not val:
                return "", ""
            return val, COLOR_MAP.get(opts.get("color", ""), "")

        if name == "cost":
            usd = meta.get("cost_usd")
            if usd is None:
                return "", ""
            try:
                digits = int(opts.get("digits", "2"))
            except (TypeError, ValueError):
                digits = 2
            try:
                v = float(usd)
            except (TypeError, ValueError):
                return "", ""
            if opts.get("hide-zero", "") and v == 0:
                return "", ""
            return fmt_cost(v, digits), COLOR_MAP.get(opts.get("color", ""), "")

        if name in ("lines_added", "lines_removed"):
            key = "lines_added" if name == "lines_added" else "lines_removed"
            n = meta.get(key)
            if n is None:
                return "", ""
            try:
                ni = int(n)
            except (TypeError, ValueError):
                return "", ""
            if opts.get("hide-zero", "") and ni == 0:
                return "", ""
            sign = "+" if name == "lines_added" else "-"
            return "{}{}".format(sign, ni), COLOR_MAP.get(opts.get("color", ""), "")

        if name == "effort":
            level = meta.get("effort_level") or ""
            if not level:
                return "", ""
            if opts.get("hide-if", "") == level:
                return "", ""
            # color 優先順位: <level>-color > color > レベル別デフォルト
            color_key = opts.get(level + "-color") or opts.get("color") or EFFORT_DEFAULT_COLORS.get(level, "")
            return level, COLOR_MAP.get(color_key, "")

        if name == "output_style":
            style = meta.get("output_style") or ""
            if not style:
                return "", ""
            if opts.get("hide-if", "") == style:
                return "", ""
            return style, COLOR_MAP.get(opts.get("color", ""), "")

        if name == "session_name":
            sn = meta.get("session_name") or ""
            if not sn:
                return "", ""
            return sn, COLOR_MAP.get(opts.get("color", ""), "")

        if name == "vim_mode":
            vm = meta.get("vim_mode") or ""
            if not vm:
                return "", ""
            if opts.get("hide-if", "") == vm:
                return "", ""
            return vm, COLOR_MAP.get(opts.get("color", ""), "")

        if name == "version":
            ver = meta.get("version") or ""
            if not ver:
                return "", ""
            return ver, COLOR_MAP.get(opts.get("color", ""), "")

        if name == "exceeds_200k":
            flag = bool(meta.get("exceeds_200k"))
            if not flag:
                return "", ""
            label = opts.get("text", "200k+")
            color_key = opts.get("color", "amber")
            return label, COLOR_MAP.get(color_key, "")

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

        elif inner.startswith("cmd:"):
            body = inner[4:]  # 'cmd:' を除去

            if body.startswith("`"):
                # バッククォートで囲まれたコマンド: エスケープを考慮して閉じバッククォートを探す
                i = 1
                while i < len(body):
                    if body[i] == "\\" and i + 1 < len(body):
                        i += 2  # エスケープシーケンスをスキップ
                    elif body[i] == "`":
                        break
                    else:
                        i += 1
                command = (
                    body[1:i]
                    .replace("\\\\", "\x00")  # \\ を一時プレースホルダーに
                    .replace("\\`", "`")  # \` → `
                    .replace("\x00", "\\")  # プレースホルダー → \
                )  # \\ → \、\` → ` に復元
                rest = body[i + 1 :]  # "|color:red" 等
                opts = {}
                if rest.startswith("|"):
                    for seg in rest[1:].split("|"):
                        opts.update(parse_options(seg))
            else:
                # バッククォートなし: text: と同じ末尾逆走査でオプション分離
                parts = body.split("|")
                opts = {}
                cmd_end = len(parts)
                for i in range(len(parts) - 1, 0, -1):
                    parsed = parse_options(parts[i])
                    if parsed:
                        opts.update(parsed)
                        cmd_end = i
                    else:
                        break
                command = "|".join(parts[:cmd_end])

            # コマンド実行
            try:
                timeout = int(opts.get("timeout", CMD_TIMEOUT))
                proc = subprocess.Popen(
                    command,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    start_new_session=True,
                )
                try:
                    stdout, _ = proc.communicate(timeout=timeout)
                    success = proc.returncode == 0
                    val = stdout.strip() if success else ""
                except subprocess.TimeoutExpired:
                    try:
                        if hasattr(os, "killpg"):
                            os.killpg(proc.pid, signal.SIGTERM)
                        else:
                            proc.terminate()
                    except ProcessLookupError:
                        pass
                    proc.communicate()
                    success = False
                    val = ""
            except Exception:
                success = False
                val = ""

            if not success:
                mode, err_text = _resolve_on_error(opts)
                if mode == "hide":
                    return ""
                if mode == "text":
                    val = err_text

            color = COLOR_MAP.get(opts.get("color", ""), "")
            if color and val:
                return color + val + RESET
            return val

        parts = inner.split("|")
        identifier = parts[0]
        opts = {}
        for p in parts[1:]:
            opts.update(parse_options(p))

        val, color = resolve(identifier, opts)
        if val:
            prefix = opts.get("prefix", "")
            suffix = opts.get("suffix", "")
            val = prefix + val + suffix
        if color and val:
            return color + val + RESET
        return val

    return re.sub(r"\{(cmd:`(?:[^`\\]|\\.)*`[^}]*|[^}]+)\}", lambda m: process_token(m.group(1)), fmt)


# ── Main ────────────────────────────────────────────────────────────────────────
def main():
    if hasattr(signal, "SIGALRM"):

        def _timeout_handler(signum, frame):
            os._exit(124)

        signal.signal(signal.SIGALRM, _timeout_handler)
        signal.alarm(GLOBAL_TIMEOUT)

    _q: queue.Queue[str | None] = queue.Queue()

    def _stdin_reader() -> None:
        try:
            _q.put(sys.stdin.read())
        except Exception:
            _q.put(None)

    threading.Thread(target=_stdin_reader, daemon=True).start()
    try:
        raw = _q.get(timeout=STDIN_TIMEOUT)
    except queue.Empty:
        raw = None
    try:
        input_data = json.loads(raw) if raw else {}
    except Exception:
        input_data = {}

    cwd_real = (input_data.get("workspace") or {}).get("current_dir") or input_data.get("cwd", "") or ""
    model = (input_data.get("model") or {}).get("display_name", "")
    ctx_remaining = (input_data.get("context_window") or {}).get("remaining_percentage")

    cost_obj = input_data.get("cost") or {}
    effort_obj = input_data.get("effort") or {}
    output_style_obj = input_data.get("output_style") or {}
    vim_obj = input_data.get("vim") or {}
    meta = {
        "cost_usd": cost_obj.get("total_cost_usd"),
        "duration_ms": cost_obj.get("total_duration_ms"),
        "api_duration_ms": cost_obj.get("total_api_duration_ms"),
        "lines_added": cost_obj.get("total_lines_added"),
        "lines_removed": cost_obj.get("total_lines_removed"),
        "effort_level": effort_obj.get("level"),
        "output_style": output_style_obj.get("name"),
        "session_name": input_data.get("session_name"),
        "vim_mode": vim_obj.get("mode"),
        "version": input_data.get("version"),
        "exceeds_200k": input_data.get("exceeds_200k_tokens"),
        "context_window": input_data.get("context_window") or {},
    }

    git_branch = get_git_branch(cwd_real) or get_git_commit(cwd_real)
    git_dirty = get_git_dirty(cwd_real) if git_branch else False
    usage = get_usage_data()

    fmt = os.environ.get("CLAUDE_NANO_LINE_FORMAT", "")
    if not fmt:
        theme_name = os.environ.get("CLAUDE_NANO_LINE_THEME", "")
        if theme_name:
            fmt = THEMES.get(theme_name, "")
    if fmt:
        output = render_custom(fmt, ctx_remaining, usage, model, cwd_real, git_branch, git_dirty, meta)
    else:
        cwd_short = str(Path(cwd_real)).replace(str(Path.home()), "~") if cwd_real else ""
        cwd_base = Path(cwd_real).name if cwd_real else ""
        if not cwd_base:
            cwd_base = cwd_short
        output = render_default(ctx_remaining, usage, model, cwd_base, git_branch, git_dirty)

    sys.stdout.write(output)
    sys.stdout.flush()


if __name__ == "__main__":
    main()
    os._exit(0)
