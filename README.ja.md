# ClaudeNanoLine

[English version](README.md)

![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)
![macOS](https://img.shields.io/badge/macOS-supported-brightgreen)
![Windows](https://img.shields.io/badge/Windows-supported-brightgreen)
![Linux](https://img.shields.io/badge/Linux-supported-brightgreen)

5時間枠・7日枠の API 利用量とリセットまでの残り時間を、1行で把握できる Claude Code ステータスラインです。

![demo](demo.png)

## スクリプト

### `claude-nano-line.py`

Claude Code の
[statusLine](https://docs.anthropic.com/ja/docs/claude-code/settings)
に設定するコマンドです。

以下の情報をターミナルのステータスバーに表示します:

- **作業ディレクトリ** と **Git ブランチ**
- **使用中のモデル名**
- **コンテキスト使用率** (緑 / 黄 / 赤でカラー表示)
- **API 使用率**: 5 時間枠・7 日枠の utilization % とリセットまでの残り時間

API 使用率は OAuth トークン（macOS はキーチェーン、Windows/Linux は
`~/.claude/.credentials.json`）を使って Anthropic API から取得します。360 秒間キャッシュします
(`$XDG_CACHE_HOME/claude-nano-line/claude-usage-cache.json`、デフォルト:
`~/.cache/claude-nano-line/`)。

## セットアップ

### 自動インストール (推奨)

```sh
curl -fsSL https://raw.githubusercontent.com/HappyOnigiri/ClaudeNanoLine/main/setup.sh | bash
```

`~/.claude/claude-nano-line.py` のダウンロードと `~/.claude/settings.json`
への設定追加を自動で行います。変更前に差分を表示して確認を求めます。

### 手動インストール

1. スクリプトを `~/.claude/` にコピーして実行権限を付与する:

```sh
cp claude-nano-line.py ~/.claude/
chmod +x ~/.claude/claude-nano-line.py
```

2. `~/.claude/settings.json` に以下を追加する:

```json
{
  "statusLine": {
    "type": "command",
    "command": "python3 ~/.claude/claude-nano-line.py"
  }
}
```

## 依存関係

- `python3` (3.7 以上)
- `security` (macOS のみ・キーチェーンアクセス用)

## Windows 対応

Git Bash または WSL 上で動作します。自動インストール・手動インストールともに、お使いの環境（Git Bash または
WSL）のシェルから実行してください。

- **認証**: Windows では macOS のキーチェーンが使えないため、`~/.claude/.credentials.json`
  からトークンを取得します。Claude Code でログイン済みであれば、このファイルは自動で作成されます。

## カスタマイズ

### テーマプリセット

フォーマット文字列を書かなくても、`CLAUDE_NANO_LINE_THEME` でビルトインテーマを指定できます:

```sh
export CLAUDE_NANO_LINE_THEME=ocean
```

| テーマ    | 説明                                     |
| --------- | ---------------------------------------- |
| `classic` | レガシーデフォルトレイアウトを再現       |
| `minimal` | 最小限: ctx%, 5h%, model, path           |
| `ocean`   | 青/シアン系カラー                        |
| `forest`  | 緑系カラー                               |
| `sunset`  | アンバー/ピンク系の暖色カラー            |
| `nerd`    | 最大情報密度: トークン数・リセット時刻付 |

`CLAUDE_NANO_LINE_FORMAT` は `CLAUDE_NANO_LINE_THEME` より優先されます。不明なテーマ名はサイレントにレガシーレイアウトへフォールバックします。

### カスタムフォーマット

環境変数 `CLAUDE_NANO_LINE_FORMAT` でステータスラインの表示内容を自由にカスタマイズできます。未設定時はデフォルトの表示になります。

### 構文

フォーマット文字列は `{type|options}` 形式のトークンで構成されます。

**値プレースホルダー**: `{name}` または `{name|options}`

```
{5h_pct}
{5h_pct|color:green,warn-color:yellow,alert-color:red,warn-threshold:70,alert-threshold:90}
{5h_reset|format:dh}
```

**リテラルテキスト**: `{text:string}` または `{text:string|options}`

```
{text:[5h]|color:gray}
{text: | |color:gray}
```

### プレースホルダー一覧

| 名前               | 出力例            | 説明                                                                  |
| ------------------ | ----------------- | --------------------------------------------------------------------- |
| `ctx_pct`          | `73%`             | コンテキスト使用率                                                    |
| `5h_pct`           | `27%`             | 5 時間枠使用率                                                        |
| `7d_pct`           | `15%`             | 7 日枠使用率                                                          |
| `5h_reset`         | `3.4h`            | 5h リセット残り時間                                                   |
| `7d_reset`         | `6d`              | 7d リセット残り時間                                                   |
| `5h_reset_at`      | `18:30`           | 5h リセット日時                                                       |
| `7d_reset_at`      | `3/25 09:00`      | 7d リセット日時                                                       |
| `model`            | `Sonnet`          | モデル名                                                              |
| `cwd`              | `myproject`       | ディレクトリ basename                                                 |
| `cwd_short`        | `~/dev/proj`      | `~` 省略パス                                                          |
| `cwd_full`         | `/Users/.../proj` | フルパス                                                              |
| `branch`           | `main`            | Git ブランチ名                                                        |
| `branch_dirty`     | `main*`           | Git ブランチ名（未コミット変更がある場合に `*` などのマーカーを付加） |
| `ctx_tokens`       | `140k`            | コンテキスト残りトークン数（モデル名から推定）                        |
| `ctx_used_tokens`  | `60k`             | コンテキスト使用トークン数（モデル名から推定）                        |
| `ctx_total_tokens` | `200k`            | コンテキスト総トークン数（モデル名から推定）                          |

### オプション一覧

| key               | 対象                     | 値                                                                                | デフォルト               | 説明                                                                                                  |
| ----------------- | ------------------------ | --------------------------------------------------------------------------------- | ------------------------ | ----------------------------------------------------------------------------------------------------- |
| `color`           | 全て                     | 色名                                                                              | なし                     | 表示色                                                                                                |
| `warn-color`      | `*_pct`                  | 色名                                                                              | `yellow`                 | 警告時の色                                                                                            |
| `alert-color`     | `*_pct`                  | 色名                                                                              | `red`                    | 危険時の色                                                                                            |
| `warn-threshold`  | `*_pct`                  | 数値                                                                              | `80`                     | 警告しきい値（%）                                                                                     |
| `alert-threshold` | `*_pct`                  | 数値                                                                              | `95`                     | 危険しきい値（%）                                                                                     |
| `format`          | `*_reset`                | `auto`/`hm`/`h1`/`dh`/`d1`                                                        | `auto`                   | 時間フォーマット（従来オプション）                                                                    |
| `unit`            | `*_reset`                | `auto` / `h` / `d` / `dh`                                                         | `auto`                   | 表示単位（`h`=時間固定, `d`=日固定, `dh`=日+時間, `auto`=自動）                                       |
| `digits`          | `*_reset`                | 数値                                                                              | `1`                      | 小数桁数（例: `digits:2` → `2.50h`）                                                                  |
| `format`          | `*_reset_at`             | `auto`/`auto_tz`/`time`/`time_tz`/`datetime`/`datetime_tz`/`full`/`full_tz`/`iso` | `auto`                   | 日時フォーマット（`auto`=今日なら時刻のみ、別日なら`M/D HH:MM`）                                      |
| `tz`              | `*_reset_at`             | `local` / `utc`                                                                   | `local`                  | 表示タイムゾーン                                                                                      |
| `dirty-suffix`    | `branch`, `branch_dirty` | 文字列                                                                            | `*` / `""`               | dirty 時に付加するサフィックス（`branch_dirty` デフォルト: `*`、`branch` はデフォルト空でオプトイン） |
| `dirty-color`     | `branch`, `branch_dirty` | 色名                                                                              | `color` にフォールバック | dirty 時の色                                                                                          |
| `haiku-color`     | `model`                  | 色名                                                                              | `amber`                  | Haiku モデル時の色                                                                                    |
| `sonnet-color`    | `model`                  | 色名                                                                              | `sky_blue`               | Sonnet モデル時の色                                                                                   |
| `opus-color`      | `model`                  | 色名                                                                              | `pink`                   | Opus モデル時の色                                                                                     |

### 使用可能な色名

`red`, `green`, `yellow`, `cyan`, `blue`, `magenta`, `gray`, `light_gray`,
`sky_blue`, `pink`, `amber`, `bold`, `bold_yellow`

### 設定例

```bash
# シンプル表示
export CLAUDE_NANO_LINE_FORMAT="{5h_pct} {7d_pct} {model}"

# カスタム色・しきい値
export CLAUDE_NANO_LINE_FORMAT="{text:[5h]|color:cyan} {5h_pct|warn-threshold:70,alert-threshold:90} {model}"

# 使用率 + リセット時間を時間単位・小数2桁で表示
export CLAUDE_NANO_LINE_FORMAT="{5h_pct} {text:(}{5h_reset|unit:h,digits:2}{text:)} {model}"

# リセット時間を日+時間で整数表示
export CLAUDE_NANO_LINE_FORMAT="{5h_pct} {text:(}{5h_reset|unit:dh,digits:0}{text:)} {7d_pct} {model}"

# モデルごとに色を変える
export CLAUDE_NANO_LINE_FORMAT="{5h_pct} {model|haiku-color:green,sonnet-color:yellow,opus-color:blue} {cwd}"

# セパレータ付き
export CLAUDE_NANO_LINE_FORMAT="{5h_pct} {text:|} {7d_pct} {text:|} {model} {cwd}"

# デフォルトの見た目を再現
export CLAUDE_NANO_LINE_FORMAT="{text:[ctx]|color:gray} {ctx_pct} {text:[5h]|color:gray} {5h_pct} {text:(|color:light_gray}{5h_reset}{text:)|color:light_gray} {text:[7d]|color:gray} {7d_pct} {text:(|color:light_gray}{7d_reset}{text:)|color:light_gray} {model} {cwd|color:bold_yellow}{text: (|color:cyan}{branch}{text:)|color:cyan}"

# コンテキストのトークン数表示（モデル名から推定）
export CLAUDE_NANO_LINE_FORMAT="{ctx_pct} {ctx_used_tokens}/{ctx_total_tokens} {model}"

# Git dirty 表示（未コミット変更があると "main*" と表示）
export CLAUDE_NANO_LINE_FORMAT="{5h_pct} {model} {cwd} {branch_dirty}"

# dirty 時に色を変える（clean: cyan、dirty: yellow）
export CLAUDE_NANO_LINE_FORMAT="{5h_pct} {model} {cwd} {branch_dirty|color:cyan,dirty-color:yellow}"

# {branch} にオプトインで dirty マーカーを付加
export CLAUDE_NANO_LINE_FORMAT="{5h_pct} {model} {cwd} {branch|dirty-suffix:!,dirty-color:red}"
```

`~/.zprofile` や `~/.bashrc` に `export` 行を追加すれば常時有効になります。

## トラブルシューティング

### API 使用率が `[5h] --%` / `[7d] --%` と表示される

- **トークン未取得**: Claude Code で一度ログインしてください。macOS はキーチェーン、Windows/Linux は
  `~/.claude/.credentials.json` にトークンが保存されます。
- **ネットワーク**: API への接続に失敗している可能性があります。ファイアウォールやプロキシ設定を確認してください。

### `Timeout` と表示される

API リクエストがタイムアウトしました。ネットワーク状況を確認し、数分後に再試行してください（360 秒キャッシュ後に完了後に自動で再取得されます）。

### `Usage API Rate Limit` と表示される

API のレート制限に達しました。しばらく待つと自動で復旧します。

### ログの確認

API 呼び出しの詳細は `$XDG_STATE_HOME/claude-nano-line/claude-usage-api.log`（デフォルト:
`~/.local/state/claude-nano-line/`）に記録されます。問題の切り分けに役立ちます。
