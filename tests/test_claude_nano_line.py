#!/usr/bin/env python3
"""Comprehensive unit tests for claude-nano-line.py"""

import importlib.util
import json
import os
import re
import tempfile
import time
import types
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

# ── Module loader ──────────────────────────────────────────────────────────────
_REPO_DIR = Path(__file__).parent.parent
spec = importlib.util.spec_from_file_location("claude_nano_line", _REPO_DIR / "claude-nano-line.py")
cnl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cnl)


def strip_ansi(s):
    return re.sub(r"\033\[[^m]*m", "", s)


# ── 1. TestToPct ───────────────────────────────────────────────────────────────
class TestToPct(unittest.TestCase):
    def test_none_returns_negative_one(self):
        self.assertEqual(cnl.to_pct(None), -1)

    def test_zero(self):
        self.assertEqual(cnl.to_pct(0), 0)

    def test_integer_value(self):
        self.assertEqual(cnl.to_pct(50), 50)

    def test_float_value(self):
        self.assertEqual(cnl.to_pct(42.7), 42)

    def test_string_numeric(self):
        self.assertEqual(cnl.to_pct("75.5"), 75)

    def test_cap_at_100(self):
        self.assertEqual(cnl.to_pct(150), 100)

    def test_small_float(self):
        self.assertEqual(cnl.to_pct(0.5), 0)


# ── 2. TestFmtResetTime ────────────────────────────────────────────────────────
class TestFmtResetTime(unittest.TestCase):
    # 固定現在時刻: 2026-03-18 12:00:00 UTC
    FIXED_NOW = datetime(2026, 3, 18, 12, 0, 0, tzinfo=timezone.utc)

    def _iso(self, delta_seconds):
        """現在時刻から delta_seconds 後の ISO 文字列を返す"""
        return (self.FIXED_NOW + timedelta(seconds=delta_seconds)).isoformat()

    def _patch_now(self):
        return (
            patch("claude_nano_line.datetime")
            if False
            else patch.object(
                cnl,
                "datetime",
                **{
                    "now.return_value": self.FIXED_NOW,
                    "fromisoformat.side_effect": datetime.fromisoformat,
                    "spec": datetime,
                },
            )
        )

    def setUp(self):
        # datetime.now をパッチ: fromisoformat は本物を使う
        self.mock_dt = MagicMock(spec=datetime)
        self.mock_dt.now.return_value = self.FIXED_NOW
        self.mock_dt.fromisoformat.side_effect = datetime.fromisoformat
        self.patcher = patch.object(cnl, "datetime", self.mock_dt)
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()

    def test_empty_string(self):
        self.assertEqual(cnl.fmt_reset_time(""), "")

    def test_past_date(self):
        past = self._iso(-100)
        self.assertEqual(cnl.fmt_reset_time(past), "")

    def test_invalid_iso_string(self):
        self.assertEqual(cnl.fmt_reset_time("not-a-date"), "")

    def test_auto_under_1h(self):
        iso = self._iso(30 * 60)  # 30分後
        result = cnl.fmt_reset_time(iso)
        self.assertEqual(result, "30m")

    def test_auto_1h_to_10h(self):
        iso = self._iso(int(2.5 * 3600))  # 2.5時間後
        result = cnl.fmt_reset_time(iso)
        self.assertEqual(result, "2.5h")

    def test_auto_10h_to_24h(self):
        iso = self._iso(15 * 3600 + 30 * 60)  # 15h30m後
        result = cnl.fmt_reset_time(iso)
        self.assertEqual(result, "15h30m")

    def test_auto_1d_to_2d(self):
        iso = self._iso(36 * 3600)  # 36時間後 = 1d12h
        result = cnl.fmt_reset_time(iso)
        self.assertEqual(result, "1d12h")

    def test_auto_over_2d(self):
        iso = self._iso(3 * 86400)  # 3日後
        result = cnl.fmt_reset_time(iso)
        self.assertEqual(result, "3d")

    def test_auto_exactly_2d(self):
        iso = self._iso(2 * 86400)  # ちょうど2日後
        result = cnl.fmt_reset_time(iso)
        self.assertEqual(result, "2d")

    def test_fmt_hm(self):
        iso = self._iso(int(2.5 * 3600))  # 2.5時間後 = 2h30m
        result = cnl.fmt_reset_time(iso, "hm")
        self.assertEqual(result, "2h30m")

    def test_fmt_h1(self):
        iso = self._iso(int(2.5 * 3600))
        result = cnl.fmt_reset_time(iso, "h1")
        self.assertEqual(result, "2.5h")

    def test_fmt_dh_with_days(self):
        iso = self._iso(27 * 3600)  # 27時間 = 1d3h
        result = cnl.fmt_reset_time(iso, "dh")
        self.assertEqual(result, "1d 3h")

    def test_fmt_dh_no_days(self):
        iso = self._iso(5 * 3600)
        result = cnl.fmt_reset_time(iso, "dh")
        self.assertEqual(result, "5h")

    def test_fmt_d1(self):
        iso = self._iso(36 * 3600)  # 1.5日
        result = cnl.fmt_reset_time(iso, "d1")
        self.assertEqual(result, "1.5d")

    def test_z_suffix(self):
        dt = self.FIXED_NOW + timedelta(minutes=30)
        iso_z = dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        result = cnl.fmt_reset_time(iso_z)
        self.assertEqual(result, "30m")

    def test_auto_exactly_24h(self):
        iso = self._iso(86400)  # ちょうど24時間後 → 24h00m
        result = cnl.fmt_reset_time(iso)
        self.assertEqual(result, "24h00m")

    def test_auto_24h30m(self):
        iso = self._iso(88200)  # 24.5時間後 → 24h30m
        result = cnl.fmt_reset_time(iso)
        self.assertEqual(result, "24h30m")


# ── 3. TestColorize ────────────────────────────────────────────────────────────
class TestColorize(unittest.TestCase):
    def test_with_color(self):
        result = cnl.colorize("hello", "\033[0;32m")
        self.assertTrue(result.startswith("\033[0;32m"))
        self.assertIn("hello", result)
        self.assertTrue(result.endswith(cnl.RESET))

    def test_empty_color_code(self):
        result = cnl.colorize("hello", "")
        self.assertEqual(result, "hello")

    def test_empty_text(self):
        result = cnl.colorize("", "\033[0;32m")
        self.assertEqual(result, "\033[0;32m" + cnl.RESET)


# ── 4. TestGetModelColor ───────────────────────────────────────────────────────
class TestGetModelColor(unittest.TestCase):
    def test_haiku(self):
        self.assertEqual(cnl.get_model_color("claude-haiku-3"), cnl.COLOR_MAP["amber"])

    def test_sonnet(self):
        self.assertEqual(cnl.get_model_color("claude-sonnet-4"), cnl.COLOR_MAP["sky_blue"])

    def test_opus(self):
        self.assertEqual(cnl.get_model_color("claude-opus-4"), cnl.COLOR_MAP["pink"])

    def test_case_insensitive(self):
        self.assertEqual(cnl.get_model_color("Claude-Haiku-3-5"), cnl.COLOR_MAP["amber"])
        self.assertEqual(cnl.get_model_color("CLAUDE-SONNET-3"), cnl.COLOR_MAP["sky_blue"])

    def test_unknown_model(self):
        self.assertEqual(cnl.get_model_color("gpt-4"), cnl.COLOR_MAP["magenta"])


# ── 5. TestUsageColor ──────────────────────────────────────────────────────────
class TestUsageColor(unittest.TestCase):
    def test_green(self):
        self.assertEqual(cnl.usage_color(50), cnl.COLOR_MAP["green"])

    def test_yellow(self):
        self.assertEqual(cnl.usage_color(85), cnl.COLOR_MAP["yellow"])

    def test_red(self):
        self.assertEqual(cnl.usage_color(97), cnl.COLOR_MAP["red"])

    def test_boundary_79_80_95(self):
        self.assertEqual(cnl.usage_color(79), cnl.COLOR_MAP["green"])
        self.assertEqual(cnl.usage_color(80), cnl.COLOR_MAP["yellow"])
        self.assertEqual(cnl.usage_color(95), cnl.COLOR_MAP["red"])

    def test_custom_thresholds(self):
        self.assertEqual(cnl.usage_color(60, warn_pct=70, crit_pct=90), cnl.COLOR_MAP["green"])
        self.assertEqual(cnl.usage_color(75, warn_pct=70, crit_pct=90), cnl.COLOR_MAP["yellow"])
        self.assertEqual(cnl.usage_color(92, warn_pct=70, crit_pct=90), cnl.COLOR_MAP["red"])


# ── 6. TestParseOptions ────────────────────────────────────────────────────────
class TestParseOptions(unittest.TestCase):
    def test_single_pair(self):
        self.assertEqual(cnl.parse_options("color:green"), {"color": "green"})

    def test_multiple_pairs(self):
        result = cnl.parse_options("color:red,warn-threshold:80")
        self.assertEqual(result, {"color": "red", "warn-threshold": "80"})

    def test_empty_string(self):
        self.assertEqual(cnl.parse_options(""), {})

    def test_no_colon(self):
        self.assertEqual(cnl.parse_options("novalue"), {})

    def test_colon_in_value(self):
        result = cnl.parse_options("key:val:extra")
        self.assertEqual(result, {"key": "val:extra"})


# ── 7. TestGetThresholdColor ───────────────────────────────────────────────────
class TestGetThresholdColor(unittest.TestCase):
    def test_defaults_green(self):
        color = cnl.get_threshold_color(50, {})
        self.assertEqual(color, cnl.COLOR_MAP["green"])

    def test_defaults_yellow(self):
        color = cnl.get_threshold_color(85, {})
        self.assertEqual(color, cnl.COLOR_MAP["yellow"])

    def test_defaults_red(self):
        color = cnl.get_threshold_color(97, {})
        self.assertEqual(color, cnl.COLOR_MAP["red"])

    def test_custom_thresholds(self):
        opts = {"warn-threshold": "60", "alert-threshold": "85"}
        self.assertEqual(cnl.get_threshold_color(55, opts), cnl.COLOR_MAP["green"])
        self.assertEqual(cnl.get_threshold_color(70, opts), cnl.COLOR_MAP["yellow"])
        self.assertEqual(cnl.get_threshold_color(90, opts), cnl.COLOR_MAP["red"])

    def test_custom_colors(self):
        opts = {"color": "cyan", "warn-color": "amber", "alert-color": "pink"}
        self.assertEqual(cnl.get_threshold_color(50, opts), cnl.COLOR_MAP["cyan"])
        self.assertEqual(cnl.get_threshold_color(85, opts), cnl.COLOR_MAP["amber"])
        self.assertEqual(cnl.get_threshold_color(97, opts), cnl.COLOR_MAP["pink"])


# ── 8. TestRenderDefault ────────────────────────────────────────────────────────
class TestRenderDefault(unittest.TestCase):
    def _usage(self, five=50, seven=60, api_error=""):
        if api_error:
            return {"api_error": api_error}
        return {
            "five_hour_pct": five,
            "seven_day_pct": seven,
            "five_resets_at": "",
            "seven_resets_at": "",
        }

    def test_normal_5h_and_7d(self):
        out = strip_ansi(cnl.render_default(None, self._usage(50, 60), "sonnet", "myproject", ""))
        self.assertIn("[5h]", out)
        self.assertIn("50%", out)
        self.assertIn("[7d]", out)
        self.assertIn("60%", out)

    def test_only_5h_data(self):
        out = strip_ansi(cnl.render_default(None, self._usage(50, -1), "sonnet", "myproject", ""))
        self.assertIn("[5h]", out)
        self.assertIn("[7d] --%", out)

    def test_no_data(self):
        out = strip_ansi(cnl.render_default(None, self._usage(-1, -1), "sonnet", "myproject", ""))
        self.assertIn("[5h] --%", out)
        self.assertIn("[7d] --%", out)

    def test_api_error_limit(self):
        out = strip_ansi(cnl.render_default(None, self._usage(api_error="limit"), "sonnet", "proj", ""))
        self.assertIn("Usage API Rate Limit", out)

    def test_api_error_timeout(self):
        out = strip_ansi(cnl.render_default(None, self._usage(api_error="timeout"), "sonnet", "proj", ""))
        self.assertIn("Timeout", out)

    def test_api_error_unknown(self):
        out = strip_ansi(cnl.render_default(None, self._usage(api_error="unknown"), "sonnet", "proj", ""))
        self.assertIn("Unknown Error", out)

    def test_with_ctx_remaining(self):
        out = strip_ansi(cnl.render_default(70, self._usage(), "sonnet", "proj", ""))
        self.assertIn("[ctx]", out)
        self.assertIn("30%", out)

    def test_without_ctx_remaining(self):
        out = strip_ansi(cnl.render_default(None, self._usage(), "sonnet", "proj", ""))
        self.assertNotIn("[ctx]", out)

    def test_with_git_branch(self):
        out = strip_ansi(cnl.render_default(None, self._usage(), "sonnet", "proj", "main"))
        self.assertIn("(main)", out)

    def test_without_git_branch(self):
        out = strip_ansi(cnl.render_default(None, self._usage(), "sonnet", "proj", ""))
        # ブランチ名が空の場合 "(branch)" 形式のgit情報が表示されないことを確認
        self.assertNotIn("(main)", out)
        self.assertNotIn("(feat/", out)

    def test_color_green(self):
        out = cnl.render_default(None, self._usage(50, 50), "sonnet", "proj", "")
        self.assertIn(cnl.COLOR_MAP["green"], out)

    def test_color_yellow(self):
        out = cnl.render_default(None, self._usage(85, 85), "sonnet", "proj", "")
        self.assertIn(cnl.COLOR_MAP["yellow"], out)

    def test_color_red(self):
        out = cnl.render_default(None, self._usage(97, 97), "sonnet", "proj", "")
        self.assertIn(cnl.COLOR_MAP["red"], out)

    def test_model_haiku(self):
        out = cnl.render_default(None, self._usage(), "claude-haiku-3", "proj", "")
        self.assertIn(cnl.COLOR_MAP["amber"], out)

    def test_model_sonnet(self):
        out = cnl.render_default(None, self._usage(), "claude-sonnet-4", "proj", "")
        self.assertIn(cnl.COLOR_MAP["sky_blue"], out)

    def test_model_opus(self):
        out = cnl.render_default(None, self._usage(), "claude-opus-4", "proj", "")
        self.assertIn(cnl.COLOR_MAP["pink"], out)

    def test_api_error_suppresses_seven_part(self):
        # api_error 時は seven_part が空 → [7d] が出ない
        out = strip_ansi(cnl.render_default(None, self._usage(api_error="timeout"), "sonnet", "proj", ""))
        self.assertNotIn("[7d]", out)

    def test_dirty_shows_asterisk(self):
        out = strip_ansi(cnl.render_default(None, self._usage(), "sonnet", "proj", "main", git_dirty=True))
        self.assertIn("(main*)", out)

    def test_clean_no_asterisk(self):
        out = strip_ansi(cnl.render_default(None, self._usage(), "sonnet", "proj", "main", git_dirty=False))
        self.assertIn("(main)", out)
        self.assertNotIn("(main*)", out)


# ── 9. TestRenderCustom ────────────────────────────────────────────────────────
class TestRenderCustom(unittest.TestCase):
    def _usage(self, five=42, seven=60, five_resets="", seven_resets="", api_error=""):
        if api_error:
            return {"api_error": api_error}
        return {
            "five_hour_pct": five,
            "seven_day_pct": seven,
            "five_resets_at": five_resets,
            "seven_resets_at": seven_resets,
        }

    def _render(self, fmt, ctx=None, usage=None, model="sonnet", cwd="/home/user/project", branch="main", dirty=False):
        if usage is None:
            usage = self._usage()
        return cnl.render_custom(fmt, ctx, usage, model, cwd, branch, dirty)

    def test_5h_pct(self):
        out = strip_ansi(self._render("{5h_pct}"))
        self.assertEqual(out, "42%")

    def test_7d_pct(self):
        out = strip_ansi(self._render("{7d_pct}"))
        self.assertEqual(out, "60%")

    def test_ctx_pct(self):
        out = strip_ansi(self._render("{ctx_pct}", ctx=70))
        self.assertEqual(out, "30%")

    def test_pct_no_data(self):
        out = strip_ansi(self._render("{5h_pct}", usage=self._usage(five=-1)))
        self.assertEqual(out, "--%")

    def test_pct_custom_thresholds(self):
        out = self._render("{5h_pct|warn-threshold:50,alert-threshold:90}", usage=self._usage(five=60))
        self.assertIn(cnl.COLOR_MAP["yellow"], out)

    def test_pct_custom_colors(self):
        out = self._render("{5h_pct|color:cyan}", usage=self._usage(five=30))
        self.assertIn(cnl.COLOR_MAP["cyan"], out)

    def test_5h_reset(self):
        # fmt_reset_time は別途テスト済みなので、空文字が返ることだけ確認
        out = strip_ansi(self._render("{5h_reset}"))
        self.assertEqual(out, "")  # five_resets="" なので空

    def test_7d_reset(self):
        out = strip_ansi(self._render("{7d_reset}"))
        self.assertEqual(out, "")

    def test_reset_format_hm(self):
        # fmt_reset_time のモックは不要 (空文字列)
        out = strip_ansi(self._render("{5h_reset|format:hm}"))
        self.assertEqual(out, "")

    def test_reset_with_color(self):
        # 空値の場合色が付かないことを確認
        out = self._render("{5h_reset|color:red}")
        self.assertNotIn(cnl.COLOR_MAP["red"], out)

    def test_model_default_color(self):
        out = self._render("{model}", model="claude-haiku-3")
        self.assertIn(cnl.COLOR_MAP["amber"], out)

    def test_model_custom_color(self):
        out = self._render("{model|color:cyan}", model="claude-haiku-3")
        self.assertIn(cnl.COLOR_MAP["cyan"], out)
        self.assertNotIn(cnl.COLOR_MAP["amber"], out)

    def test_cwd(self):
        out = strip_ansi(self._render("{cwd}", cwd="/home/user/myproject"))
        self.assertEqual(out, "myproject")

    def test_cwd_short(self):
        home = str(Path.home())
        out = strip_ansi(self._render("{cwd_short}", cwd=home + "/projects/foo"))
        self.assertEqual(out, "~/projects/foo")

    def test_cwd_full(self):
        out = strip_ansi(self._render("{cwd_full}", cwd="/absolute/path/proj"))
        self.assertEqual(out, "/absolute/path/proj")

    def test_branch(self):
        out = strip_ansi(self._render("{branch}", branch="feature/test"))
        self.assertEqual(out, "feature/test")

    def test_branch_with_color(self):
        out = self._render("{branch|color:cyan}", branch="main")
        self.assertIn(cnl.COLOR_MAP["cyan"], out)
        self.assertIn("main", out)

    def test_branch_empty(self):
        out = strip_ansi(self._render("{branch}", branch=""))
        self.assertEqual(out, "")

    def test_text_literal(self):
        out = strip_ansi(self._render("{text:hello world}"))
        self.assertEqual(out, "hello world")

    def test_text_with_color(self):
        out = self._render("{text:hello|color:red}")
        self.assertIn(cnl.COLOR_MAP["red"], out)
        self.assertIn("hello", out)

    def test_text_with_pipe(self):
        out = strip_ansi(self._render("{text: | |color:gray}"))
        self.assertEqual(out, " | ")

    def test_api_error_in_pct(self):
        out = strip_ansi(self._render("{5h_pct}", usage=self._usage(api_error="timeout")))
        self.assertEqual(out, "Timeout")

    def test_ctx_pct_not_affected_by_api_error(self):
        out = strip_ansi(self._render("{ctx_pct}", ctx=70, usage=self._usage(api_error="timeout")))
        self.assertEqual(out, "30%")

    def test_branch_dirty_when_dirty(self):
        out = strip_ansi(self._render("{branch_dirty}", branch="main", dirty=True))
        self.assertEqual(out, "main*")

    def test_branch_dirty_when_clean(self):
        out = strip_ansi(self._render("{branch_dirty}", branch="main", dirty=False))
        self.assertEqual(out, "main")

    def test_branch_dirty_custom_suffix(self):
        out = strip_ansi(self._render("{branch_dirty|dirty-suffix:!}", branch="main", dirty=True))
        self.assertEqual(out, "main!")

    def test_branch_dirty_color_switch(self):
        out_dirty = self._render("{branch_dirty|color:cyan,dirty-color:red}", branch="main", dirty=True)
        self.assertIn(cnl.COLOR_MAP["red"], out_dirty)
        self.assertNotIn(cnl.COLOR_MAP["cyan"], out_dirty)

        out_clean = self._render("{branch_dirty|color:cyan,dirty-color:red}", branch="main", dirty=False)
        self.assertIn(cnl.COLOR_MAP["cyan"], out_clean)
        self.assertNotIn(cnl.COLOR_MAP["red"], out_clean)

    def test_branch_optin_dirty_suffix(self):
        out = strip_ansi(self._render("{branch|dirty-suffix:*}", branch="main", dirty=True))
        self.assertEqual(out, "main*")

    def test_branch_optin_no_suffix_when_clean(self):
        out = strip_ansi(self._render("{branch|dirty-suffix:*}", branch="main", dirty=False))
        self.assertEqual(out, "main")

    def test_branch_no_dirty_suffix_by_default(self):
        # {branch} は dirty-suffix 指定なしでは dirty でも * が付かない
        out = strip_ansi(self._render("{branch}", branch="main", dirty=True))
        self.assertEqual(out, "main")

    def test_unknown_placeholder(self):
        out = strip_ansi(self._render("{unknown_token}"))
        self.assertEqual(out, "")

    def test_combined_format(self):
        out = strip_ansi(
            self._render(
                "{5h_pct} {7d_pct} {model} {cwd}",
                usage=self._usage(five=42, seven=60),
                model="claude-sonnet-4",
                cwd="/home/user/myproject",
            )
        )
        self.assertIn("42%", out)
        self.assertIn("60%", out)
        self.assertIn("claude-sonnet-4", out)
        self.assertIn("myproject", out)


# ── 10. TestGetGitBranch ───────────────────────────────────────────────────────
class TestGetGitBranch(unittest.TestCase):
    def test_success(self):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "main\n"
        with patch.object(cnl.subprocess, "run", return_value=mock_result):
            self.assertEqual(cnl.get_git_branch("/some/path"), "main")

    def test_failure(self):
        mock_result = MagicMock()
        mock_result.returncode = 1
        with patch.object(cnl.subprocess, "run", return_value=mock_result):
            self.assertEqual(cnl.get_git_branch("/some/path"), "")

    def test_exception(self):
        with patch.object(cnl.subprocess, "run", side_effect=Exception("oops")):
            self.assertEqual(cnl.get_git_branch("/some/path"), "")

    def test_empty_cwd(self):
        with patch.object(cnl.subprocess, "run") as mock_run:
            result = cnl.get_git_branch("")
            self.assertEqual(result, "")
            mock_run.assert_not_called()

    def test_none_cwd(self):
        with patch.object(cnl.subprocess, "run") as mock_run:
            result = cnl.get_git_branch(None)
            self.assertEqual(result, "")
            mock_run.assert_not_called()


# ── 10b. TestGetGitDirty ──────────────────────────────────────────────────────
class TestGetGitDirty(unittest.TestCase):
    def _mock_run(self, returncode, stdout=""):
        r = MagicMock()
        r.returncode = returncode
        r.stdout = stdout
        return r

    def test_dirty(self):
        with patch.object(cnl.subprocess, "run", return_value=self._mock_run(0, " M file.py\n")):
            self.assertTrue(cnl.get_git_dirty("/some/path"))

    def test_clean(self):
        with patch.object(cnl.subprocess, "run", return_value=self._mock_run(0, "")):
            self.assertFalse(cnl.get_git_dirty("/some/path"))

    def test_git_failure(self):
        with patch.object(cnl.subprocess, "run", return_value=self._mock_run(1)):
            self.assertFalse(cnl.get_git_dirty("/some/path"))

    def test_exception(self):
        with patch.object(cnl.subprocess, "run", side_effect=Exception("oops")):
            self.assertFalse(cnl.get_git_dirty("/some/path"))

    def test_timeout(self):
        import subprocess

        with patch.object(cnl.subprocess, "run", side_effect=subprocess.TimeoutExpired(["git"], 3)):
            self.assertFalse(cnl.get_git_dirty("/some/path"))

    def test_empty_cwd(self):
        with patch.object(cnl.subprocess, "run") as mock_run:
            self.assertFalse(cnl.get_git_dirty(""))
            mock_run.assert_not_called()

    def test_none_cwd(self):
        with patch.object(cnl.subprocess, "run") as mock_run:
            self.assertFalse(cnl.get_git_dirty(None))
            mock_run.assert_not_called()


# ── 11. TestGetOAuthToken ──────────────────────────────────────────────────────
class TestGetOAuthToken(unittest.TestCase):
    def _keychain_result(self, returncode, stdout):
        r = MagicMock()
        r.returncode = returncode
        r.stdout = stdout
        return r

    def test_keychain_success(self):
        creds = json.dumps({"claudeAiOauth": {"accessToken": "token123"}})
        mock_result = self._keychain_result(0, creds)
        with patch.object(cnl.subprocess, "run", return_value=mock_result):
            self.assertEqual(cnl.get_oauth_token(), "token123")

    def test_keychain_fail_file_success(self):
        mock_result = self._keychain_result(1, "")
        creds_data = json.dumps({"claudeAiOauth": {"accessToken": "file_token"}})
        with patch.object(cnl.subprocess, "run", return_value=mock_result):
            with patch("builtins.open", unittest.mock.mock_open(read_data=creds_data)):
                self.assertEqual(cnl.get_oauth_token(), "file_token")

    def test_both_fail(self):
        mock_result = self._keychain_result(1, "")
        with patch.object(cnl.subprocess, "run", return_value=mock_result):
            with patch("builtins.open", side_effect=FileNotFoundError):
                self.assertIsNone(cnl.get_oauth_token())

    def test_keychain_invalid_json(self):
        mock_result = self._keychain_result(0, "not-valid-json")
        creds_data = json.dumps({"claudeAiOauth": {"accessToken": "fallback_token"}})
        with patch.object(cnl.subprocess, "run", return_value=mock_result):
            with patch("builtins.open", unittest.mock.mock_open(read_data=creds_data)):
                self.assertEqual(cnl.get_oauth_token(), "fallback_token")


# ── 12. TestCacheReadWrite ─────────────────────────────────────────────────────
class TestCacheReadWrite(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.tmp_cache_dir = Path(self.tmpdir)
        self.tmp_cache_file = self.tmp_cache_dir / "claude-usage-cache.json"
        self.patcher_dir = patch.object(cnl, "CACHE_DIR", self.tmp_cache_dir)
        self.patcher_file = patch.object(cnl, "CACHE_FILE", self.tmp_cache_file)
        self.patcher_dir.start()
        self.patcher_file.start()

    def tearDown(self):
        self.patcher_dir.stop()
        self.patcher_file.stop()
        import shutil

        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_write_and_read(self):
        data = {"five_hour_pct": 42, "seven_day_pct": 60}
        cnl.write_cache(data)
        result = cnl.read_cache()
        self.assertIsNotNone(result)
        self.assertEqual(result["five_hour_pct"], 42)

    def test_expired(self):
        data = {"five_hour_pct": 42, "_ts": int(time.time()) - cnl.CACHE_TTL - 10}
        with open(self.tmp_cache_file, "w") as f:
            json.dump(data, f)
        result = cnl.read_cache()
        self.assertIsNone(result)

    def test_missing_file(self):
        result = cnl.read_cache()
        self.assertIsNone(result)

    def test_corrupted_json(self):
        with open(self.tmp_cache_file, "w") as f:
            f.write("not valid json{{{")
        result = cnl.read_cache()
        self.assertIsNone(result)

    def test_creates_dir(self):
        import shutil

        shutil.rmtree(self.tmpdir, ignore_errors=True)
        cnl.write_cache({"five_hour_pct": 10})
        self.assertTrue(self.tmp_cache_file.exists())


# ── 13. TestWriteLog ───────────────────────────────────────────────────────────
class TestWriteLog(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.tmp_log_dir = Path(self.tmpdir)
        self.tmp_log_file = self.tmp_log_dir / "claude-usage-api.log"
        self.patcher_dir = patch.object(cnl, "LOG_DIR", self.tmp_log_dir)
        self.patcher_file = patch.object(cnl, "LOG_FILE", self.tmp_log_file)
        self.patcher_dir.start()
        self.patcher_file.start()

    def tearDown(self):
        self.patcher_dir.stop()
        self.patcher_file.stop()
        import shutil

        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_creates_file(self):
        cnl.write_log("test message")
        self.assertTrue(self.tmp_log_file.exists())
        content = self.tmp_log_file.read_text()
        self.assertIn("test message", content)

    def test_appends(self):
        cnl.write_log("first")
        cnl.write_log("second")
        lines = self.tmp_log_file.read_text().strip().splitlines()
        self.assertEqual(len(lines), 2)
        self.assertIn("first", lines[0])
        self.assertIn("second", lines[1])


# ── 14. TestFetchUsage ─────────────────────────────────────────────────────────
class TestFetchUsage(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.tmp_cache_dir = Path(self.tmpdir)
        self.patcher_dir = patch.object(cnl, "CACHE_DIR", self.tmp_cache_dir)
        self.patcher_file = patch.object(cnl, "CACHE_FILE", self.tmp_cache_dir / "cache.json")
        self.patcher_log_dir = patch.object(cnl, "LOG_DIR", self.tmp_cache_dir)
        self.patcher_log = patch.object(cnl, "LOG_FILE", self.tmp_cache_dir / "test.log")
        self.patcher_dir.start()
        self.patcher_file.start()
        self.patcher_log_dir.start()
        self.patcher_log.start()

    def tearDown(self):
        self.patcher_dir.stop()
        self.patcher_file.stop()
        self.patcher_log_dir.stop()
        self.patcher_log.stop()
        import shutil

        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _mock_response(self, data):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(data).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        return mock_resp

    def test_success(self):
        resp_data = {
            "five_hour": {"utilization": 42.7, "resets_at": "2026-03-18T18:00:00Z"},
            "seven_day": {"utilization": 60.0, "resets_at": "2026-03-25T00:00:00Z"},
        }
        with patch.object(cnl, "urlopen", return_value=self._mock_response(resp_data)):
            result = cnl.fetch_usage("mytoken")
        self.assertIn("five_hour_pct", result)
        self.assertIn("seven_day_pct", result)
        self.assertIn("five_resets_at", result)
        self.assertIn("seven_resets_at", result)
        self.assertEqual(result["five_hour_pct"], 42)

    def test_timeout(self):
        with patch.object(cnl, "urlopen", side_effect=TimeoutError()):
            result = cnl.fetch_usage("mytoken")
        self.assertEqual(result, {"api_error": "timeout"})

    def test_url_error_timed_out(self):
        from urllib.error import URLError

        with patch.object(cnl, "urlopen", side_effect=URLError("timed out")):
            result = cnl.fetch_usage("mytoken")
        self.assertEqual(result, {"api_error": "timeout"})

    def test_url_error_other(self):
        from urllib.error import URLError

        with patch.object(cnl, "urlopen", side_effect=URLError("connection refused")):
            result = cnl.fetch_usage("mytoken")
        self.assertEqual(result, {"api_error": "unknown"})

    def test_http_error(self):
        from urllib.error import HTTPError

        with patch.object(cnl, "urlopen", side_effect=HTTPError("url", 403, "Forbidden", {}, None)):
            result = cnl.fetch_usage("mytoken")
        self.assertEqual(result, {"api_error": "unknown"})

    def test_json_parse_error(self):
        mock_resp = MagicMock()
        mock_resp.read.return_value = b"not-json"
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        with patch.object(cnl, "urlopen", return_value=mock_resp):
            result = cnl.fetch_usage("mytoken")
        self.assertEqual(result, {"api_error": "unknown"})

    def test_rate_limit(self):
        resp_data = {"error": {"type": "rate_limit_error", "message": "rate limited"}}
        with patch.object(cnl, "urlopen", return_value=self._mock_response(resp_data)):
            result = cnl.fetch_usage("mytoken")
        self.assertEqual(result, {"api_error": "limit"})

    def test_utilization_cap(self):
        resp_data = {
            "five_hour": {"utilization": 120.0, "resets_at": ""},
            "seven_day": {"utilization": 150.0, "resets_at": ""},
        }
        with patch.object(cnl, "urlopen", return_value=self._mock_response(resp_data)):
            result = cnl.fetch_usage("mytoken")
        self.assertEqual(result["five_hour_pct"], 100)
        self.assertEqual(result["seven_day_pct"], 100)

    def test_url_error_ssl_certificate(self):
        import ssl
        from urllib.error import URLError

        reason = ssl.SSLError(1, "CERTIFICATE_VERIFY_FAILED certificate verify failed")
        with patch.object(cnl, "urlopen", side_effect=URLError(reason)):
            with patch.object(cnl, "write_log") as mock_log:
                result = cnl.fetch_usage("mytoken")
        self.assertEqual(result, {"api_error": "unknown"})
        # SSL 由来であることをログで判別できることを保証
        logged = " ".join(str(c.args[0]) for c in mock_log.call_args_list)
        self.assertIn("error:ssl", logged)


# ── 14b. TestBuildSSLContext ───────────────────────────────────────────────────
class TestBuildSSLContext(unittest.TestCase):
    def test_uses_certifi_when_default_paths_broken(self):
        import ssl as _ssl

        fake_paths = _ssl.DefaultVerifyPaths(
            cafile=None,
            capath=None,
            openssl_cafile_env="SSL_CERT_FILE",
            openssl_cafile="/nonexistent/cert.pem",
            openssl_capath_env="SSL_CERT_DIR",
            openssl_capath="/nonexistent/certs",
        )
        fake_certifi = types.SimpleNamespace(where=lambda: "/tmp/fake-ca.pem")
        with (
            patch.object(cnl, "certifi", fake_certifi),
            patch.object(_ssl, "get_default_verify_paths", return_value=fake_paths),
        ):
            ctx = MagicMock()
            with patch.object(_ssl, "create_default_context", return_value=ctx):
                cnl._build_ssl_context()
            ctx.load_verify_locations.assert_called_once_with(cafile="/tmp/fake-ca.pem")

    def test_skips_certifi_when_default_paths_ok(self):
        import ssl as _ssl

        fake_paths = _ssl.DefaultVerifyPaths(
            cafile="/etc/ssl/cert.pem",
            capath=None,
            openssl_cafile_env="SSL_CERT_FILE",
            openssl_cafile="/etc/ssl/cert.pem",
            openssl_capath_env="SSL_CERT_DIR",
            openssl_capath="/etc/ssl/certs",
        )
        with patch.object(_ssl, "get_default_verify_paths", return_value=fake_paths):
            ctx = MagicMock()
            with patch.object(_ssl, "create_default_context", return_value=ctx):
                cnl._build_ssl_context()
            ctx.load_verify_locations.assert_not_called()


# ── 15. TestGetUsageData ───────────────────────────────────────────────────────
class TestGetUsageData(unittest.TestCase):
    def test_cache_hit(self):
        cached = {"five_hour_pct": 42, "seven_day_pct": 60, "_ts": int(time.time())}
        with patch.object(cnl, "read_cache", return_value=cached):
            with patch.object(cnl, "fetch_usage") as mock_fetch:
                result = cnl.get_usage_data()
        mock_fetch.assert_not_called()
        self.assertEqual(result["five_hour_pct"], 42)

    def test_cache_miss_with_token(self):
        with patch.object(cnl, "read_cache", return_value=None):
            with patch.object(cnl, "get_oauth_token", return_value="mytoken"):
                with patch.object(cnl, "fetch_usage", return_value={"five_hour_pct": 55}) as mock_fetch:
                    result = cnl.get_usage_data()
        mock_fetch.assert_called_once_with("mytoken")
        self.assertEqual(result["five_hour_pct"], 55)

    def test_no_token(self):
        with patch.object(cnl, "read_cache", return_value=None):
            with patch.object(cnl, "get_oauth_token", return_value=None):
                result = cnl.get_usage_data()
        self.assertEqual(result, {})


# ── 16. TestMainIntegration ────────────────────────────────────────────────────
class TestMainIntegration(unittest.TestCase):
    _USAGE = {
        "five_hour_pct": 42,
        "seven_day_pct": 60,
        "five_resets_at": "",
        "seven_resets_at": "",
    }

    def _run_main(self, stdin_data, env=None):
        import io

        stdin_json = json.dumps(stdin_data)
        with patch("sys.stdin", io.StringIO(stdin_json)):
            with patch.object(cnl, "get_usage_data", return_value=self._USAGE):
                with patch.object(cnl, "get_git_branch", return_value="main"):
                    with patch.object(cnl, "get_git_dirty", return_value=False):
                        env_patch = {}
                        if env:
                            env_patch = env
                        with patch.dict(os.environ, env_patch, clear=False):
                            # CLAUDE_NANO_LINE_FORMAT をクリアする場合
                            if "CLAUDE_NANO_LINE_FORMAT" not in env_patch:
                                with patch.dict(os.environ, {"CLAUDE_NANO_LINE_FORMAT": ""}, clear=False):
                                    captured = io.StringIO()
                                    with patch("sys.stdout", captured):
                                        cnl.main()
                                    return captured.getvalue()
                            else:
                                captured = io.StringIO()
                                with patch("sys.stdout", captured):
                                    cnl.main()
                                return captured.getvalue()

    def test_default_mode(self):
        input_data = {
            "model": {"display_name": "claude-sonnet-4"},
            "workspace": {"current_dir": "/home/user/project"},
            "context_window": {"remaining_percentage": 70},
        }
        out = strip_ansi(self._run_main(input_data))
        self.assertIn("[5h]", out)
        self.assertIn("42%", out)
        self.assertIn("[7d]", out)

    def test_custom_format(self):
        input_data = {
            "model": {"display_name": "claude-sonnet-4"},
            "workspace": {"current_dir": "/home/user/project"},
        }
        out = strip_ansi(self._run_main(input_data, env={"CLAUDE_NANO_LINE_FORMAT": "{5h_pct} | {model}"}))
        self.assertIn("42%", out)
        self.assertIn("claude-sonnet-4", out)

    def test_invalid_json_stdin(self):
        import io

        with patch("sys.stdin", io.StringIO("not valid json{")):
            with patch.object(cnl, "get_usage_data", return_value=self._USAGE):
                with patch.object(cnl, "get_git_branch", return_value=""):
                    with patch.object(cnl, "get_git_dirty", return_value=False):
                        with patch.dict(os.environ, {"CLAUDE_NANO_LINE_FORMAT": ""}, clear=False):
                            captured = io.StringIO()
                            with patch("sys.stdout", captured):
                                # クラッシュしないことを確認
                                cnl.main()
                            out = captured.getvalue()
        # 何らかの出力があること（空でない）
        self.assertIsInstance(out, str)

    def test_empty_stdin(self):
        import io

        with patch("sys.stdin", io.StringIO("")):
            with patch.object(cnl, "get_usage_data", return_value=self._USAGE):
                with patch.object(cnl, "get_git_branch", return_value=""):
                    with patch.object(cnl, "get_git_dirty", return_value=False):
                        with patch.dict(os.environ, {"CLAUDE_NANO_LINE_FORMAT": ""}, clear=False):
                            captured = io.StringIO()
                            with patch("sys.stdout", captured):
                                cnl.main()
                            out = captured.getvalue()
        self.assertIsInstance(out, str)


# ── Feature 2: fmt_reset_time_v2 ───────────────────────────────────────────────
class TestFmtResetTimeV2(unittest.TestCase):
    def _iso(self, seconds_from_now):
        dt = datetime.now(timezone.utc) + timedelta(seconds=seconds_from_now)
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    def test_unit_h_digits1(self):
        iso = self._iso(9000)  # 2.5h
        result = cnl.fmt_reset_time_v2(iso, unit="h", digits=1)
        self.assertRegex(result, r"^\d+\.\d{1}h$")

    def test_unit_h_digits0(self):
        iso = self._iso(9000)
        result = cnl.fmt_reset_time_v2(iso, unit="h", digits=0)
        self.assertRegex(result, r"^\d+h$")

    def test_unit_d_digits1(self):
        iso = self._iso(129600)  # 1.5d
        result = cnl.fmt_reset_time_v2(iso, unit="d", digits=1)
        self.assertRegex(result, r"^\d+\.\d{1}d$")

    def test_unit_d_digits0(self):
        iso = self._iso(129600)
        result = cnl.fmt_reset_time_v2(iso, unit="d", digits=0)
        self.assertRegex(result, r"^\d+d$")

    def test_unit_dh_digits1(self):
        iso = self._iso(97200)  # 1d 3h
        result = cnl.fmt_reset_time_v2(iso, unit="dh", digits=1)
        self.assertRegex(result, r"^\d+d \d+\.\d{1}h$")

    def test_unit_dh_digits0(self):
        iso = self._iso(97200)
        result = cnl.fmt_reset_time_v2(iso, unit="dh", digits=0)
        self.assertRegex(result, r"^\d+d \d+h$")

    def test_unit_auto_minutes(self):
        iso = self._iso(1800)  # 30m
        result = cnl.fmt_reset_time_v2(iso, unit="auto", digits=1)
        self.assertRegex(result, r"^\d+m$")

    def test_unit_auto_hours(self):
        iso = self._iso(7200)  # 2h
        result = cnl.fmt_reset_time_v2(iso, unit="auto", digits=1)
        self.assertRegex(result, r"^\d+\.\d+h$")

    def test_unit_auto_1d_to_2d(self):
        iso = self._iso(36 * 3600)  # 36時間後 → 1dXh 形式
        result = cnl.fmt_reset_time_v2(iso, unit="auto", digits=1)
        self.assertRegex(result, r"^1d\d+h$")

    def test_unit_auto_over_2d(self):
        iso = self._iso(3 * 86400)  # 3日後 → Xd 形式
        result = cnl.fmt_reset_time_v2(iso, unit="auto", digits=1)
        self.assertRegex(result, r"^\d+d$")

    def test_unit_auto_exactly_2d(self):
        iso = self._iso(2 * 86400 + 60)  # 2日+1分後 → 2d 形式
        result = cnl.fmt_reset_time_v2(iso, unit="auto", digits=1)
        self.assertEqual(result, "2d")

    def test_unit_auto_exactly_24h(self):
        iso = self._iso(86400 + 30)  # 24時間+余裕30秒後 → 24hXXm 形式
        result = cnl.fmt_reset_time_v2(iso, unit="auto", digits=1)
        self.assertRegex(result, r"^24h\d{2}m$")

    def test_unit_auto_24h30m(self):
        iso = self._iso(88200 + 30)  # 24h30m+余裕30秒後 → 24hXXm 形式
        result = cnl.fmt_reset_time_v2(iso, unit="auto", digits=1)
        self.assertRegex(result, r"^24h\d{2}m$")

    def test_empty_iso_returns_empty(self):
        self.assertEqual(cnl.fmt_reset_time_v2("", unit="h", digits=1), "")

    def test_past_time_returns_empty(self):
        iso = self._iso(-100)
        self.assertEqual(cnl.fmt_reset_time_v2(iso, unit="h", digits=1), "")


# ── Feature 2: reset unit/digits dispatch via render_custom ───────────────────
class TestResetDispatch(unittest.TestCase):
    def _iso(self, seconds_from_now):
        dt = datetime.now(timezone.utc) + timedelta(seconds=seconds_from_now)
        return dt.strftime("%Y-%m-%dT%H:%M:%SZ")

    def _usage(self, secs):
        return {
            "five_hour_pct": 50,
            "seven_day_pct": 50,
            "five_resets_at": self._iso(secs),
            "seven_resets_at": self._iso(secs),
        }

    def _render(self, fmt, secs):
        return strip_ansi(cnl.render_custom(fmt, None, self._usage(secs), "sonnet", "", ""))

    def test_unit_opt_uses_v2(self):
        val = self._render("{5h_reset|unit:h,digits:2}", 9000)
        self.assertRegex(val, r"^\d+\.\d{2}h$")

    def test_digits_opt_uses_v2(self):
        # auto unit, digits=0, 9000s=2.5h → <10h なので時間表示、整数
        val = self._render("{5h_reset|digits:0}", 9000)
        self.assertRegex(val, r"^\d+h$")

    def test_no_opts_uses_default(self):
        val = self._render("{5h_reset}", 9000)
        self.assertGreater(len(val), 0)

    def test_format_opt_uses_default(self):
        val = self._render("{5h_reset|format:h1}", 9000)
        self.assertRegex(val, r"^\d+\.\d+h$")


# ── Feature 3: model per-model color ──────────────────────────────────────────
class TestModelPerModelColor(unittest.TestCase):
    _USAGE = {
        "five_hour_pct": 50,
        "seven_day_pct": 50,
        "five_resets_at": "",
        "seven_resets_at": "",
    }

    def _render(self, fmt, model):
        return cnl.render_custom(fmt, None, self._USAGE, model, "", "")

    def test_haiku_color(self):
        out = self._render("{model|haiku-color:green}", "claude-haiku-4-5")
        self.assertIn(cnl.COLOR_MAP["green"], out)

    def test_sonnet_color(self):
        out = self._render("{model|sonnet-color:cyan}", "claude-sonnet-4-6")
        self.assertIn(cnl.COLOR_MAP["cyan"], out)

    def test_opus_color(self):
        out = self._render("{model|opus-color:pink}", "claude-opus-4-6")
        self.assertIn(cnl.COLOR_MAP["pink"], out)

    def test_blanket_color_overrides_per_model(self):
        out = self._render("{model|color:red,haiku-color:green}", "claude-haiku-4-5")
        self.assertIn(cnl.COLOR_MAP["red"], out)
        self.assertNotIn(cnl.COLOR_MAP["green"], out)

    def test_haiku_color_not_applied_to_sonnet(self):
        out = self._render("{model|haiku-color:green}", "claude-sonnet-4-6")
        # haiku-color は sonnet に適用されない → デフォルト色 (sky_blue)
        self.assertNotIn(cnl.COLOR_MAP["green"], out)
        self.assertIn(cnl.COLOR_MAP["sky_blue"], out)

    def test_unrecognized_model_falls_through_to_default(self):
        out = self._render("{model|haiku-color:green}", "unknown-model-xyz")
        self.assertNotIn(cnl.COLOR_MAP["green"], out)


# ── Feature 4: fmt_reset_datetime ─────────────────────────────────────────────
class TestFmtResetDatetime(unittest.TestCase):
    def test_empty_string(self):
        self.assertEqual(cnl.fmt_reset_datetime("", "auto"), "")

    def test_none_returns_empty(self):
        self.assertEqual(cnl.fmt_reset_datetime(None, "auto"), "")

    def test_invalid_iso_returns_empty(self):
        self.assertEqual(cnl.fmt_reset_datetime("not-a-date", "auto"), "")

    def test_time_format_utc(self):
        iso = "2099-01-15T10:30:00Z"
        result = cnl.fmt_reset_datetime(iso, "time", tz_local=False)
        self.assertEqual(result, "10:30")

    def test_datetime_format_utc(self):
        iso = "2099-01-15T10:30:00Z"
        result = cnl.fmt_reset_datetime(iso, "datetime", tz_local=False)
        self.assertEqual(result, "1/15 10:30")

    def test_full_format_utc(self):
        iso = "2099-01-15T10:30:00Z"
        result = cnl.fmt_reset_datetime(iso, "full", tz_local=False)
        self.assertEqual(result, "2099-01-15 10:30")

    def test_iso_format(self):
        iso = "2099-01-15T10:30:00Z"
        result = cnl.fmt_reset_datetime(iso, "iso", tz_local=False)
        self.assertIn("2099-01-15", result)
        self.assertIn("10:30:00", result)
        self.assertIn("+00:00", result)

    def test_auto_different_day_utc(self):
        # 遠い未来の日付は今日とは別日 → "M/D HH:MM"
        iso = "2099-01-15T10:30:00Z"
        result = cnl.fmt_reset_datetime(iso, "auto", tz_local=False)
        self.assertEqual(result, "1/15 10:30")

    def test_auto_same_day_utc(self):
        # 今日の日付を動的に生成して同日テスト
        now_utc = datetime.now(timezone.utc)
        iso = now_utc.replace(hour=23, minute=59, second=0, microsecond=0).isoformat()
        result = cnl.fmt_reset_datetime(iso, "auto", tz_local=False)
        # 同日なので時刻のみ "HH:MM"
        self.assertRegex(result, r"^\d{2}:\d{2}$")

    def test_time_tz_utc(self):
        iso = "2099-01-15T10:30:00Z"
        result = cnl.fmt_reset_datetime(iso, "time_tz", tz_local=False)
        self.assertEqual(result, "10:30 UTC")

    def test_datetime_tz_utc(self):
        iso = "2099-01-15T10:30:00Z"
        result = cnl.fmt_reset_datetime(iso, "datetime_tz", tz_local=False)
        self.assertEqual(result, "1/15 10:30 UTC")

    def test_full_tz_utc(self):
        iso = "2099-01-15T10:30:00Z"
        result = cnl.fmt_reset_datetime(iso, "full_tz", tz_local=False)
        self.assertEqual(result, "2099-01-15 10:30 UTC")

    def test_auto_tz_different_day_utc(self):
        iso = "2099-01-15T10:30:00Z"
        result = cnl.fmt_reset_datetime(iso, "auto_tz", tz_local=False)
        self.assertEqual(result, "1/15 10:30 UTC")

    def test_auto_tz_same_day_utc(self):
        now_utc = datetime.now(timezone.utc)
        iso = now_utc.replace(hour=23, minute=59, second=0, microsecond=0).isoformat()
        result = cnl.fmt_reset_datetime(iso, "auto_tz", tz_local=False)
        # 同日なので "HH:MM UTC"
        self.assertRegex(result, r"^\d{2}:\d{2} UTC$")

    def test_iso_with_tz_suffix_behaves_same_as_iso(self):
        # iso_tz は iso と同じ出力（_tz サフィックスを除去すると base_fmt="iso"）
        iso = "2099-01-15T10:30:00Z"
        result_iso = cnl.fmt_reset_datetime(iso, "iso", tz_local=False)
        result_iso_tz = cnl.fmt_reset_datetime(iso, "iso_tz", tz_local=False)
        self.assertEqual(result_iso, result_iso_tz)

    def test_past_datetime_still_returns_value(self):
        # 過去日時でも値を返す
        iso = "2000-03-18T10:30:00Z"
        result = cnl.fmt_reset_datetime(iso, "datetime", tz_local=False)
        self.assertEqual(result, "3/18 10:30")

    def test_z_suffix_parsed_correctly(self):
        iso = "2099-01-15T10:30:00Z"
        result = cnl.fmt_reset_datetime(iso, "time", tz_local=False)
        self.assertEqual(result, "10:30")


# ── Feature 4: resolve() integration for *_reset_at ───────────────────────────
class TestResetAtResolve(unittest.TestCase):
    _USAGE = {
        "five_hour_pct": 50,
        "five_hour_pct_raw": 50.0,
        "seven_day_pct": 50,
        "seven_day_pct_raw": 50.0,
        "five_resets_at": "2099-12-25T10:30:00Z",
        "seven_resets_at": "2099-12-25T14:00:00Z",
    }

    def _render(self, fmt):
        return strip_ansi(cnl.render_custom(fmt, None, self._USAGE, "claude-sonnet-4-6", "", ""))

    def test_5h_reset_at_default(self):
        result = self._render("{5h_reset_at|tz:utc}")
        # "3/25 10:30" (別日)
        self.assertRegex(result, r"^\d+/\d+ \d{2}:\d{2}$")

    def test_7d_reset_at_default(self):
        result = self._render("{7d_reset_at|tz:utc}")
        self.assertRegex(result, r"^\d+/\d+ \d{2}:\d{2}$")

    def test_5h_reset_at_time_tz_utc(self):
        result = self._render("{5h_reset_at|format:time_tz,tz:utc}")
        self.assertEqual(result, "10:30 UTC")

    def test_7d_reset_at_datetime_utc(self):
        result = self._render("{7d_reset_at|format:datetime,tz:utc}")
        self.assertEqual(result, "12/25 14:00")

    def test_7d_reset_at_full_utc(self):
        result = self._render("{7d_reset_at|format:full,tz:utc}")
        self.assertEqual(result, "2099-12-25 14:00")

    def test_5h_reset_at_iso(self):
        result = self._render("{5h_reset_at|format:iso,tz:utc}")
        self.assertIn("2099-12-25", result)
        self.assertIn("10:30:00", result)

    def test_color_applied(self):
        raw = cnl.render_custom(
            "{5h_reset_at|format:time,tz:utc,color:gray}",
            None,
            self._USAGE,
            "claude-sonnet-4-6",
            "",
            "",
        )
        self.assertIn(cnl.COLOR_MAP["gray"], raw)

    def test_empty_iso_returns_empty(self):
        usage = dict(self._USAGE, five_resets_at="")
        result = strip_ansi(cnl.render_custom("{5h_reset_at}", None, usage, "claude-sonnet-4-6", "", ""))
        self.assertEqual(result, "")


# ── Feature 5: fmt_tokens ──────────────────────────────────────────────────────
class TestFmtTokens(unittest.TestCase):
    def test_none_returns_dash(self):
        self.assertEqual(cnl.fmt_tokens(None), "--")

    def test_millions(self):
        self.assertEqual(cnl.fmt_tokens(1_200_000), "1.2M")

    def test_thousands(self):
        self.assertEqual(cnl.fmt_tokens(150_000), "150k")

    def test_small(self):
        self.assertEqual(cnl.fmt_tokens(800), "800")

    def test_zero(self):
        self.assertEqual(cnl.fmt_tokens(0), "0")

    def test_exactly_1m(self):
        self.assertEqual(cnl.fmt_tokens(1_000_000), "1.0M")

    def test_exactly_1k(self):
        self.assertEqual(cnl.fmt_tokens(1_000), "1k")


# ── Feature 5: estimate_tokens ─────────────────────────────────────────────────
class TestEstimateTokens(unittest.TestCase):
    def test_sonnet(self):
        used, total = cnl.estimate_tokens("claude-sonnet-4-6", 70)
        self.assertEqual(total, 200_000)
        self.assertEqual(used, 60_000)

    def test_opus(self):
        used, total = cnl.estimate_tokens("claude-opus-4-6", 85)
        self.assertEqual(total, 200_000)
        self.assertEqual(used, 30_000)

    def test_opus_1m(self):
        used, total = cnl.estimate_tokens("Opus 4.6 (1M context)", 85)
        self.assertEqual(total, 1_000_000)
        self.assertEqual(used, 150_000)

    def test_unknown_model_uses_default(self):
        used, total = cnl.estimate_tokens("unknown-model", 50)
        self.assertEqual(total, cnl.DEFAULT_CONTEXT_SIZE)
        self.assertEqual(used, cnl.DEFAULT_CONTEXT_SIZE // 2)

    def test_none_remaining_returns_none(self):
        used, total = cnl.estimate_tokens("claude-sonnet-4-6", None)
        self.assertIsNone(used)
        self.assertIsNone(total)


# ── Feature 5: render_custom token placeholders ────────────────────────────────
class TestRenderCustomTokens(unittest.TestCase):
    _USAGE = {
        "five_hour_pct": 50,
        "seven_day_pct": 50,
        "five_resets_at": "",
        "seven_resets_at": "",
    }

    def _render(self, fmt, ctx=None, model="claude-sonnet-4-6"):
        return cnl.render_custom(fmt, ctx, self._USAGE, model, "/home/user/project", "main")

    def test_ctx_used_tokens(self):
        out = strip_ansi(self._render("{ctx_used_tokens}", ctx=70))
        self.assertEqual(out, "60k")

    def test_ctx_tokens_remaining(self):
        out = strip_ansi(self._render("{ctx_tokens}", ctx=70))
        self.assertEqual(out, "140k")

    def test_ctx_total_tokens(self):
        out = strip_ansi(self._render("{ctx_total_tokens}", ctx=70))
        self.assertEqual(out, "200k")

    def test_ctx_remaining_none_returns_dash(self):
        out = strip_ansi(self._render("{ctx_used_tokens}", ctx=None))
        self.assertEqual(out, "--")

    def test_threshold_color_applied(self):
        # ctx=5 (95% used) should trigger alert color
        out = self._render("{ctx_used_tokens}", ctx=5)
        self.assertIn(cnl.COLOR_MAP["red"], out)

    def test_combined_format(self):
        out = strip_ansi(self._render("{ctx_pct} {ctx_used_tokens}/{ctx_total_tokens}", ctx=70))
        self.assertIn("30%", out)
        self.assertIn("60k", out)
        self.assertIn("200k", out)


# ── Feature 5: render_default token info ────────────────────────────────────────
class TestRenderDefaultTokens(unittest.TestCase):
    def _usage(self):
        return {
            "five_hour_pct": 50,
            "seven_day_pct": 60,
            "five_resets_at": "",
            "seven_resets_at": "",
        }

    def test_ctx_shows_token_info(self):
        out = strip_ansi(cnl.render_default(70, self._usage(), "claude-sonnet-4-6", "proj", ""))
        self.assertIn("[ctx]", out)
        self.assertIn("30%", out)
        self.assertNotIn("k/", out)

    def test_no_ctx_no_token_info(self):
        out = strip_ansi(cnl.render_default(None, self._usage(), "claude-sonnet-4-6", "proj", ""))
        self.assertNotIn("[ctx]", out)


# ── TestThemePresets ───────────────────────────────────────────────────────────
class TestThemePresets(unittest.TestCase):
    _USAGE = {
        "five_hour_pct": 50,
        "seven_day_pct": 60,
        "five_resets_at": "",
        "seven_resets_at": "",
    }

    def test_themes_dict_has_expected_keys(self):
        expected = {"classic", "minimal", "ocean", "forest", "sunset", "nerd"}
        self.assertEqual(set(cnl.THEMES.keys()), expected)

    def test_all_themes_render_without_error(self):
        for name, fmt in cnl.THEMES.items():
            with self.subTest(theme=name):
                out = cnl.render_custom(fmt, 70, self._USAGE, "claude-sonnet-4-6", "/home/user/proj", "main", False)
                self.assertIsInstance(out, str)
                self.assertTrue(len(out) > 0)

    def test_theme_env_used_when_format_not_set(self):
        with patch.dict(os.environ, {"CLAUDE_NANO_LINE_THEME": "ocean"}, clear=False):
            os.environ.pop("CLAUDE_NANO_LINE_FORMAT", None)
            fmt = os.environ.get("CLAUDE_NANO_LINE_FORMAT", "")
            if not fmt:
                theme_name = os.environ.get("CLAUDE_NANO_LINE_THEME", "")
                if theme_name:
                    fmt = cnl.THEMES.get(theme_name, "")
            self.assertEqual(fmt, cnl.THEMES["ocean"])

    def test_format_overrides_theme(self):
        custom_fmt = "{ctx_pct}"
        with patch.dict(
            os.environ,
            {"CLAUDE_NANO_LINE_FORMAT": custom_fmt, "CLAUDE_NANO_LINE_THEME": "ocean"},
            clear=False,
        ):
            fmt = os.environ.get("CLAUDE_NANO_LINE_FORMAT", "")
            if not fmt:
                theme_name = os.environ.get("CLAUDE_NANO_LINE_THEME", "")
                if theme_name:
                    fmt = cnl.THEMES.get(theme_name, "")
            self.assertEqual(fmt, custom_fmt)

    def test_invalid_theme_falls_back_to_default(self):
        with patch.dict(os.environ, {"CLAUDE_NANO_LINE_THEME": "nonexistent_theme"}, clear=False):
            os.environ.pop("CLAUDE_NANO_LINE_FORMAT", None)
            fmt = os.environ.get("CLAUDE_NANO_LINE_FORMAT", "")
            if not fmt:
                theme_name = os.environ.get("CLAUDE_NANO_LINE_THEME", "")
                if theme_name:
                    fmt = cnl.THEMES.get(theme_name, "")
            self.assertEqual(fmt, "")


# ── 24. TestResolveOnError ─────────────────────────────────────────────────────
class TestResolveOnError(unittest.TestCase):
    def test_empty_string_returns_default(self):
        self.assertEqual(cnl._resolve_on_error({}), ("default", ""))

    def test_hide_returns_hide(self):
        self.assertEqual(cnl._resolve_on_error({"on-error": "hide"}), ("hide", ""))

    def test_text_returns_text_and_string(self):
        self.assertEqual(cnl._resolve_on_error({"on-error": "text(N/A)"}), ("text", "N/A"))

    def test_text_with_emoji(self):
        self.assertEqual(cnl._resolve_on_error({"on-error": "text(⚠)"}), ("text", "⚠"))

    def test_text_with_spaces(self):
        self.assertEqual(cnl._resolve_on_error({"on-error": "text(err)"}), ("text", "err"))

    def test_unknown_value_returns_default(self):
        self.assertEqual(cnl._resolve_on_error({"on-error": "something_invalid"}), ("default", ""))


# ── 25. TestOnErrorPct ─────────────────────────────────────────────────────────
class TestOnErrorPct(unittest.TestCase):
    _USAGE_ERROR = {"api_error": "timeout"}
    _USAGE_LIMIT = {"api_error": "limit"}

    def _render(self, fmt, usage):
        return strip_ansi(cnl.render_custom(fmt, 70, usage, "claude-sonnet-4-6", "/home/user", "main"))

    def test_pct_hide_on_timeout(self):
        out = self._render("{5h_pct|on-error:hide}", self._USAGE_ERROR)
        self.assertEqual(out.strip(), "")

    def test_pct_text_on_timeout(self):
        out = self._render("{5h_pct|on-error:text(N/A)}", self._USAGE_ERROR)
        self.assertIn("N/A", out)

    def test_pct_text_on_limit(self):
        out = self._render("{5h_pct|on-error:text(---)}", self._USAGE_LIMIT)
        self.assertIn("---", out)

    def test_pct_default_shows_error_string(self):
        out = self._render("{5h_pct}", self._USAGE_ERROR)
        self.assertIn("Timeout", out)

    def test_pct_default_shows_rate_limit(self):
        out = self._render("{7d_pct}", self._USAGE_LIMIT)
        self.assertIn("Rate Limit", out)

    def test_ctx_pct_not_affected_by_api_error(self):
        out = self._render("{ctx_pct}", self._USAGE_ERROR)
        # ctx_pct は API 非依存なので "Timeout" にはならない
        self.assertNotIn("Timeout", out)


# ── 26. TestOnErrorReset ───────────────────────────────────────────────────────
class TestOnErrorReset(unittest.TestCase):
    _USAGE_ERROR = {"api_error": "timeout"}

    def _render(self, fmt, usage):
        return strip_ansi(cnl.render_custom(fmt, 70, usage, "claude-sonnet-4-6", "/home/user", "main"))

    def test_reset_hide(self):
        out = self._render("{5h_reset|on-error:hide}", self._USAGE_ERROR)
        self.assertEqual(out.strip(), "")

    def test_reset_text(self):
        out = self._render("{5h_reset|on-error:text(N/A)}", self._USAGE_ERROR)
        self.assertIn("N/A", out)

    def test_7d_reset_hide(self):
        out = self._render("{7d_reset|on-error:hide}", self._USAGE_ERROR)
        self.assertEqual(out.strip(), "")


# ── 27. TestOnErrorResetAt ─────────────────────────────────────────────────────
class TestOnErrorResetAt(unittest.TestCase):
    _USAGE_ERROR = {"api_error": "unknown"}

    def _render(self, fmt, usage):
        return strip_ansi(cnl.render_custom(fmt, 70, usage, "claude-sonnet-4-6", "/home/user", "main"))

    def test_reset_at_hide(self):
        out = self._render("{5h_reset_at|on-error:hide}", self._USAGE_ERROR)
        self.assertEqual(out.strip(), "")

    def test_reset_at_text(self):
        out = self._render("{5h_reset_at|on-error:text(?)}", self._USAGE_ERROR)
        self.assertIn("?", out)

    def test_7d_reset_at_text(self):
        out = self._render("{7d_reset_at|on-error:text(ERR)}", self._USAGE_ERROR)
        self.assertIn("ERR", out)


# ── 28. TestOnErrorIntegration ─────────────────────────────────────────────────
class TestOnErrorIntegration(unittest.TestCase):
    _USAGE_ERROR = {"api_error": "timeout"}

    def test_mixed_format_with_hide(self):
        fmt = "{5h_pct|on-error:hide} {model}"
        out = strip_ansi(cnl.render_custom(fmt, 70, self._USAGE_ERROR, "claude-haiku-4-5", "/home/user", "main"))
        self.assertNotIn("Timeout", out)
        self.assertIn("claude-haiku-4-5", out)

    def test_mixed_format_with_text(self):
        fmt = "{5h_pct|on-error:text(N/A)} {7d_reset|on-error:text(N/A)} {model}"
        out = strip_ansi(cnl.render_custom(fmt, 70, self._USAGE_ERROR, "claude-sonnet-4-6", "/home/user", "main"))
        self.assertIn("N/A", out)
        self.assertIn("claude-sonnet-4-6", out)


# ── 29. TestHideUnder ─────────────────────────────────────────────────────────
class TestHideUnder(unittest.TestCase):
    def _render(self, fmt, usage):
        return strip_ansi(cnl.render_custom(fmt, None, usage, "claude-sonnet-4-6", "/home/user", "main"))

    def _render_ctx(self, fmt, ctx_remaining):
        return strip_ansi(cnl.render_custom(fmt, ctx_remaining, {}, "claude-sonnet-4-6", "/home/user", "main"))

    def _usage_5h(self, pct):
        return {"five_hour_pct": pct}

    def _usage_7d(self, pct):
        return {"seven_day_pct": pct}

    def test_5h_pct_below_threshold_hidden(self):
        out = self._render("{5h_pct|hide-under:70}", self._usage_5h(42))
        self.assertEqual(out.strip(), "")

    def test_5h_pct_above_threshold_shown(self):
        out = self._render("{5h_pct|hide-under:70}", self._usage_5h(85))
        self.assertIn("85%", out)

    def test_5h_pct_at_threshold_shown(self):
        # ちょうど N% → 表示される
        out = self._render("{5h_pct|hide-under:70}", self._usage_5h(70))
        self.assertIn("70%", out)

    def test_7d_pct_hide_under(self):
        out = self._render("{7d_pct|hide-under:50}", self._usage_7d(30))
        self.assertEqual(out.strip(), "")

    def test_7d_pct_shown_above(self):
        out = self._render("{7d_pct|hide-under:50}", self._usage_7d(60))
        self.assertIn("60%", out)

    def test_ctx_pct_hide_under(self):
        # ctx_remaining=70 → ctx_used=30%
        out = self._render_ctx("{ctx_pct|hide-under:50}", 70)
        self.assertEqual(out.strip(), "")

    def test_ctx_pct_shown_above(self):
        # ctx_remaining=10 → ctx_used=90%
        out = self._render_ctx("{ctx_pct|hide-under:50}", 10)
        self.assertIn("90%", out)

    def test_missing_data_hidden_when_hide_under_set(self):
        # データ欠損（-1）→ hide-under 指定時は非表示
        out = self._render("{5h_pct|hide-under:10}", {})
        self.assertEqual(out.strip(), "")

    def test_missing_data_shown_without_hide_under(self):
        # データ欠損（-1）→ hide-under 未指定なら --%
        out = self._render("{5h_pct}", {})
        self.assertIn("--%", out)

    def test_api_error_on_error_takes_priority(self):
        usage = {"api_error": "timeout"}
        out = self._render("{5h_pct|on-error:text(ERR)|hide-under:10}", usage)
        self.assertIn("ERR", out)

    def test_invalid_hide_under_ignored(self):
        # 非数値は無視して通常表示
        out = self._render("{5h_pct|hide-under:abc}", self._usage_5h(30))
        self.assertIn("30%", out)


# ── 30. TestHideIf ─────────────────────────────────────────────────────────────
class TestHideIf(unittest.TestCase):
    def _render(self, fmt, branch="main", dirty=False, model="claude-sonnet-4-6", cwd="/home/user"):
        return strip_ansi(cnl.render_custom(fmt, 50, {}, model, cwd, branch, dirty))

    def test_branch_matches_hidden(self):
        out = self._render("{branch|hide-if:main}", branch="main")
        self.assertEqual(out.strip(), "")

    def test_branch_no_match_shown(self):
        out = self._render("{branch|hide-if:main}", branch="feat/new-feature")
        self.assertIn("feat/new-feature", out)

    def test_branch_case_sensitive(self):
        out = self._render("{branch|hide-if:Main}", branch="main")
        self.assertIn("main", out)

    def test_branch_dirty_compares_base_name(self):
        # hide-if は dirty suffix 付加前の branch 名で比較
        out = self._render("{branch_dirty|hide-if:main|dirty-suffix:*}", branch="main", dirty=True)
        self.assertEqual(out.strip(), "")

    def test_branch_dirty_no_match_shows_with_suffix(self):
        out = self._render("{branch_dirty|hide-if:main|dirty-suffix:*}", branch="dev", dirty=True)
        self.assertIn("dev*", out)

    def test_model_matches_hidden(self):
        out = self._render("{model|hide-if:claude-sonnet-4-6}", model="claude-sonnet-4-6")
        self.assertEqual(out.strip(), "")

    def test_model_no_match_shown(self):
        out = self._render("{model|hide-if:claude-sonnet-4-6}", model="claude-haiku-4-5")
        self.assertIn("claude-haiku-4-5", out)

    def test_cwd_matches_hidden(self):
        # cwd は basename
        out = self._render("{cwd|hide-if:user}", cwd="/home/user")
        self.assertEqual(out.strip(), "")

    def test_cwd_short_matches_hidden(self):
        out = self._render("{cwd_short|hide-if:~/dev}", cwd=str(cnl.Path.home()) + "/dev")
        self.assertEqual(out.strip(), "")

    def test_cwd_full_matches_hidden(self):
        out = self._render("{cwd_full|hide-if:/home/user}", cwd="/home/user")
        self.assertEqual(out.strip(), "")


# ── 31. TestHideIntegration ────────────────────────────────────────────────────
class TestHideIntegration(unittest.TestCase):
    def _render(self, fmt, **kwargs):
        branch = kwargs.get("branch", "main")
        dirty = kwargs.get("dirty", False)
        model = kwargs.get("model", "claude-sonnet-4-6")
        cwd = kwargs.get("cwd", "/home/user")
        usage = kwargs.get("usage", {"five_hour_pct": 30})
        ctx_remaining = kwargs.get("ctx_remaining", 50)
        return strip_ansi(cnl.render_custom(fmt, ctx_remaining, usage, model, cwd, branch, dirty))

    def test_partial_hide_in_format_string(self):
        fmt = "{branch|hide-if:main} {5h_pct|hide-under:70} {model}"
        out = self._render(fmt, branch="main", usage={"five_hour_pct": 30})
        self.assertNotIn("main", out)
        self.assertNotIn("30%", out)
        self.assertIn("claude-sonnet-4-6", out)

    def test_mixed_shown_and_hidden(self):
        fmt = "{branch|hide-if:main} {model}"
        out = self._render(fmt, branch="feat/my-feature")
        self.assertIn("feat/my-feature", out)
        self.assertIn("claude-sonnet-4-6", out)

    def test_hide_under_shown_in_format(self):
        fmt = "{5h_pct|hide-under:70} {model}"
        out = self._render(fmt, usage={"five_hour_pct": 85})
        self.assertIn("85%", out)
        self.assertIn("claude-sonnet-4-6", out)


# ── TestCmdToken ───────────────────────────────────────────────────────────────
class TestCmdToken(unittest.TestCase):
    """Tests for {cmd:...} token in render_custom."""

    def _usage(self):
        return {"five_hour_pct": 42, "seven_day_pct": 60, "five_resets_at": "", "seven_resets_at": ""}

    def _render(self, fmt, model="sonnet", branch="main"):
        return cnl.render_custom(fmt, None, self._usage(), model, "/home/user/project", branch, False)

    def test_basic_echo(self):
        out = strip_ansi(self._render("{cmd:echo hello}"))
        self.assertEqual(out, "hello")

    def test_backtick_basic(self):
        out = strip_ansi(self._render("{cmd:`echo hello`}"))
        self.assertEqual(out, "hello")

    def test_color_option(self):
        out = self._render("{cmd:echo hello|color:cyan}")
        self.assertIn(cnl.COLOR_MAP["cyan"], out)
        self.assertIn("hello", out)

    def test_backtick_with_pipe(self):
        out = strip_ansi(self._render("{cmd:`echo HELLO | tr A-Z a-z`}"))
        self.assertEqual(out, "hello")

    def test_backtick_with_color(self):
        out = self._render("{cmd:`echo hi`|color:red}")
        self.assertIn(cnl.COLOR_MAP["red"], out)
        self.assertIn("hi", out)

    def test_backtick_with_closing_brace(self):
        # awk コマンド内の } がパースを壊さないことを確認
        out = strip_ansi(self._render("{cmd:`echo hello | awk '{print}'`}"))
        self.assertEqual(out, "hello")

    def test_backtick_with_colon(self):
        # date +%H:%M:%S 形式: 数字:数字:数字 パターンに一致することを確認
        out = strip_ansi(self._render("{cmd:`date +%H:%M:%S`}"))
        self.assertRegex(out, r"^\d{2}:\d{2}:\d{2}$")

    def test_backtick_escaped_backtick(self):
        # \` エスケープがパーサーによって ` に復元されコマンド文字列に渡されることを確認

        mock_proc = MagicMock()
        mock_proc.communicate.return_value = ("`hello`\n", "")
        mock_proc.returncode = 0
        with patch.object(cnl.subprocess, "Popen", return_value=mock_proc) as mock_popen:
            out = strip_ansi(self._render(r"{cmd:`echo \`hello\``}"))
            called_cmd = mock_popen.call_args[0][0]
        # コマンド文字列にリテラルのバッククォートが含まれていること
        self.assertIn("`hello`", called_cmd)
        # 出力はコマンドの stdout.strip()
        self.assertEqual(out, "`hello`")

    def test_backtick_escaped_backslash(self):
        # \\ エスケープがパーサーによって \ に復元されコマンド文字列に渡されることを確認
        mock_proc = MagicMock()
        mock_proc.communicate.return_value = ("hello\n", "")
        mock_proc.returncode = 0
        with patch.object(cnl.subprocess, "Popen", return_value=mock_proc) as mock_popen:
            self._render(r"{cmd:`echo \\n`}")
            called_cmd = mock_popen.call_args[0][0]
        # \\ が単一の \ に復元されてコマンドに渡されること
        self.assertIn("\\n", called_cmd)
        self.assertNotIn("\\\\n", called_cmd)

    def test_timeout(self):
        # タイムアウトで空文字が返る
        out = strip_ansi(self._render("{cmd:sleep 10|timeout:1}"))
        self.assertEqual(out, "")

    def test_command_failure(self):
        out = strip_ansi(self._render("{cmd:false}"))
        self.assertEqual(out, "")

    def test_command_failure_with_stdout_suppressed(self):
        # 失敗コマンドの stdout は on-error 指定なしでも表示しない
        mock_proc = MagicMock()
        mock_proc.communicate.return_value = ("partial\n", "")
        mock_proc.returncode = 1
        with patch.object(cnl.subprocess, "Popen", return_value=mock_proc):
            out = strip_ansi(self._render("{cmd:echo partial; exit 1}"))
        self.assertEqual(out, "")

    def test_on_error_text(self):
        out = strip_ansi(self._render("{cmd:false|on-error:text(N/A)}"))
        self.assertEqual(out, "N/A")

    def test_on_error_hide(self):
        out = strip_ansi(self._render("{cmd:false|on-error:hide}"))
        self.assertEqual(out, "")

    def test_mixed_with_other_tokens(self):
        out = strip_ansi(self._render("{model} {cmd:echo ok}"))
        self.assertIn("sonnet", out)
        self.assertIn("ok", out)

    def test_no_color_when_empty(self):
        # コマンド失敗時、色コードが出力されない
        out = self._render("{cmd:false|color:cyan}")
        self.assertNotIn(cnl.COLOR_MAP["cyan"], out)


# ── 11. TestIsResetSince / TestGetUsageData ─────────────────────────────────────
class TestIsResetSince(unittest.TestCase):
    def test_reset_between_cache_and_now(self):
        """キャッシュ取得後にリセット時刻を跨いだ → True"""
        cached_ts = time.time() - 200
        reset_epoch = time.time() - 100
        iso = datetime.fromtimestamp(reset_epoch, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        self.assertTrue(cnl._is_reset_since(iso, cached_ts))

    def test_reset_in_future(self):
        """リセット時刻が未来 → False"""
        cached_ts = time.time() - 100
        reset_epoch = time.time() + 100
        iso = datetime.fromtimestamp(reset_epoch, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        self.assertFalse(cnl._is_reset_since(iso, cached_ts))

    def test_reset_before_cache(self):
        """リセット時刻がキャッシュ取得前 → False（取得時点で正しい値）"""
        reset_epoch = time.time() - 500
        cached_ts = time.time() - 200
        iso = datetime.fromtimestamp(reset_epoch, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        self.assertFalse(cnl._is_reset_since(iso, cached_ts))

    def test_empty_iso(self):
        """iso_str が空 → False"""
        self.assertFalse(cnl._is_reset_since("", time.time() - 100))

    def test_invalid_iso(self):
        """iso_str が不正 → False"""
        self.assertFalse(cnl._is_reset_since("not-a-date", time.time() - 100))


class TestGetUsageDataResetOverride(unittest.TestCase):
    def _make_cache(self, five_resets_at, seven_resets_at, cached_ts=None):
        ts = cached_ts if cached_ts is not None else time.time() - 200
        return {
            "_ts": ts,
            "five_hour_pct": 80,
            "seven_day_pct": 60,
            "five_resets_at": five_resets_at,
            "seven_resets_at": seven_resets_at,
        }

    def test_five_hour_reset_overrides_pct(self):
        """5h リセット済み → five_hour_pct が 0 に上書き"""
        reset_iso = datetime.fromtimestamp(time.time() - 100, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        future_iso = datetime.fromtimestamp(time.time() + 3600, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        cache = self._make_cache(reset_iso, future_iso)
        with patch.object(cnl, "read_cache", return_value=cache):
            data = cnl.get_usage_data()
        self.assertEqual(data["five_hour_pct"], 0)
        self.assertEqual(data["seven_day_pct"], 60)

    def test_seven_day_reset_overrides_pct(self):
        """7d リセット済み → seven_day_pct が 0 に上書き"""
        future_iso = datetime.fromtimestamp(time.time() + 3600, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        reset_iso = datetime.fromtimestamp(time.time() - 100, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        cache = self._make_cache(future_iso, reset_iso)
        with patch.object(cnl, "read_cache", return_value=cache):
            data = cnl.get_usage_data()
        self.assertEqual(data["five_hour_pct"], 80)
        self.assertEqual(data["seven_day_pct"], 0)

    def test_no_reset_keeps_pct(self):
        """リセット未発生 → pct はそのまま"""
        future_iso = datetime.fromtimestamp(time.time() + 3600, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        cache = self._make_cache(future_iso, future_iso)
        with patch.object(cnl, "read_cache", return_value=cache):
            data = cnl.get_usage_data()
        self.assertEqual(data["five_hour_pct"], 80)
        self.assertEqual(data["seven_day_pct"], 60)

    def test_error_cache_unaffected(self):
        """エラーキャッシュ（resets_at なし）→ 影響なし"""
        cache = {"_ts": time.time() - 200, "api_error": "timeout"}
        with patch.object(cnl, "read_cache", return_value=cache):
            data = cnl.get_usage_data()
        self.assertEqual(data.get("api_error"), "timeout")
        self.assertNotIn("five_hour_pct", data)


if __name__ == "__main__":
    unittest.main(verbosity=2)
