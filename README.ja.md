# ClaudeNanoLine

[English version](README.md)

![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)
![macOS](https://img.shields.io/badge/macOS-supported-5a8a6a.svg)
![Windows](https://img.shields.io/badge/Windows-supported-5a8a6a.svg)
![Linux](https://img.shields.io/badge/Linux-supported-5a8a6a.svg)

Claude Code の [statusLine](https://docs.anthropic.com/ja/docs/claude-code/settings) をフォーマット文字列で自由に組み立てられるツールです。

![demo](.github/assets/demo.png)

## 特徴

シェルの `$PS1` のように、**1行のフォーマット文字列で表示内容・色・条件をすべてコントロール**できます。

```bash
export CLAUDE_NANO_LINE_FORMAT="{5h_pct} {7d_pct} {model} {cwd} ({branch})"
```

- **表示できる情報** — API 使用率 (5h / 7d)、リセット残り時間、コンテキスト消費量、モデル名、Git ブランチ、作業ディレクトリなど
- **細かく調整できる** — しきい値で色を変える、条件で項目を隠す、時刻フォーマットを指定するなど、項目ごとにオプションを設定可能
- **テーマも用意** — フォーマット文字列を書かなくても `ocean`, `nerd` などのプリセットですぐ使える
- **軽量** — Python 単体で動作、外部パッケージ不要。API レスポンスは 360 秒キャッシュ

## クイックスタート

```sh
# 1. インストール
curl -fsSL https://raw.githubusercontent.com/HappyOnigiri/ClaudeNanoLine/main/setup.sh | bash

# 2. 好みのフォーマットを設定（省略するとデフォルト表示）
export CLAUDE_NANO_LINE_FORMAT="{5h_pct} {model} {cwd} ({branch})"

# 3. Claude Code を起動するとステータスラインに反映
claude
```

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

![themes](.github/assets/themes.png)

```sh
export CLAUDE_NANO_LINE_THEME=ocean
```

| テーマ    | 説明                                                                       |
| --------- | -------------------------------------------------------------------------- |
| `classic` | デフォルトレイアウトを再現                                                 |
| `minimal` | 最小限: ctx%, 5h%, model, path                                             |
| `ocean`   | 青/シアン系カラー                                                          |
| `forest`  | 緑系カラー                                                                 |
| `sunset`  | アンバー/ピンク系の暖色カラー                                              |
| `nerd`    | 最大情報密度: トークン数・リセット時刻付                                   |
| `harmony` | 寒色セグメントプライミング (ctx/5h/7d→空/シアン/緑)。右側に Claude Code ネイティブのセッションメタ（差分行数・経過時間・コスト・effort）。暖色は warn/alert 専用 |

`CLAUDE_NANO_LINE_FORMAT` は `CLAUDE_NANO_LINE_THEME` より優先されます。不明なテーマ名はサイレントにデフォルトレイアウトへフォールバックします。

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

**シェルコマンドの出力**: `{cmd:コマンド}` または `` {cmd:`コマンド`|options} ``

シェルコマンドを実行し、その標準出力をステータスラインに埋め込みます。

```
{cmd:date +%H:%M}
{cmd:date +%H:%M|color:cyan}
{cmd:`uptime | awk '{print $NF}'`|color:yellow}
```

コマンドに `|`、`:`、`}` が含まれる場合はバッククォートで囲みます。バッククォート内では `` \` `` でリテラルのバッククォート、`\\` でリテラルのバックスラッシュを表します。

> **Tip — 環境変数のクォート**: コマンドにダブルクォートが含まれる場合（例: `date "+%Y-%m-%d %H:%M"`）、`export` の値全体をシングルクォートで囲むとシェルに剥がされずに済みます：
> ```bash
> export CLAUDE_NANO_LINE_FORMAT='{cmd:date "+%Y-%m-%d %H:%M"|color:cyan} {model}'
> ```
> ダブルクォートのまま書きたい場合は内側のダブルクォートを `\"` でエスケープします：
> ```bash
> export CLAUDE_NANO_LINE_FORMAT="{cmd:date \"+%Y-%m-%d %H:%M\"|color:cyan} {model}"
> ```

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
| `repo`             | `ClaudeNanoLine`  | リポジトリ名（`workspace.repo.name` から。取れない場合は本体リポジトリのディレクトリ名にフォールバックするため、`cd` しても git worktree 内でも変わらない） |
| `repo_owner`       | `HappyOnigiri`    | リポジトリのオーナー名（`workspace.repo.owner` から。remote 不明なら空） |
| `repo_full`        | `HappyOnigiri/ClaudeNanoLine` | `owner/name`（オーナー名が不明なら空）                    |
| `branch`           | `main`            | Git ブランチ名                                                        |
| `branch_dirty`     | `main*`           | Git ブランチ名（未コミット変更がある場合に `*` などのマーカーを付加） |
| `ctx_tokens`       | `140k`            | コンテキスト残りトークン数（モデル名から推定）                        |
| `ctx_used_tokens`  | `60k`             | コンテキスト使用トークン数（モデル名から推定）                        |
| `ctx_total_tokens` | `200k`            | コンテキスト総トークン数（モデル名から推定）                          |
| `duration`         | `14m` / `2h12m`   | セッションの経過時間（`cost.total_duration_ms` から）                 |
| `api_duration`     | `47s`             | API 待ち時間の合計（`cost.total_api_duration_ms` から）               |
| `cost`             | `$0.42`           | セッション推定コスト（`cost.total_cost_usd` から）                    |
| `lines_added`      | `+156`            | このセッションで追加された行数（`cost.total_lines_added` から）       |
| `lines_removed`    | `-23`             | このセッションで削除された行数（`cost.total_lines_removed` から）     |
| `effort`           | `max`             | reasoning effort レベル（`effort.level` から）。デフォルト色: low=yellow, medium=green, high=sky\_blue, xhigh=purple, max=red |
| `output_style`     | `default`         | アクティブな output style（`output_style.name` から）                 |
| `session_name`     | `audit-pr`        | カスタムセッション名（`session_name` から）                           |
| `vim_mode`         | `NORMAL`          | Vim モード（vim editor mode 有効時、`vim.mode` から）                 |
| `version`          | `2.1.90`          | Claude Code バージョン（`version` から）                              |
| `exceeds_200k`     | `200k+`           | トークン総量が 200k を超えた時に表示するインジケータ                  |

### オプション一覧

| key               | 対象                     | 値                                                                                | デフォルト               | 説明                                                                                                  |
| ----------------- | ------------------------ | --------------------------------------------------------------------------------- | ------------------------ | ----------------------------------------------------------------------------------------------------- |
| `color`           | 全て                     | 色名                                                                              | なし                     | 表示色                                                                                                |
| `prefix`          | 全ての値プレースホルダー | 文字列                                                                            | なし                     | 解決後の値が空でないときだけ、値の前に挿入する文字列。`text:` / `cmd:` トークンには適用されない       |
| `suffix`          | 全ての値プレースホルダー | 文字列                                                                            | なし                     | 解決後の値が空でないときだけ、値の後ろに付加する文字列。`text:` / `cmd:` トークンには適用されない     |
| `warn-color`      | `*_pct`                  | 色名                                                                              | `yellow`                 | 警告時の色                                                                                            |
| `alert-color`     | `*_pct`                  | 色名                                                                              | `red`                    | 危険時の色                                                                                            |
| `warn-threshold`  | `*_pct`                  | 数値                                                                              | `80`                     | 警告しきい値（%）                                                                                     |
| `alert-threshold` | `*_pct`                  | 数値                                                                              | `95`                     | 危険しきい値（%）                                                                                     |
| `format`          | `*_reset`                | `auto`/`hm`/`h1`/`dh`/`d1`                                                        | `auto`                   | 時間フォーマット（従来オプション）                                                                    |
| `unit`            | `*_reset`                | `auto` / `h` / `d` / `dh`                                                         | `auto`                   | 表示単位（`h`=時間固定, `d`=日固定, `dh`=日+時間, `auto`=自動）                                       |
| `digits`          | `*_reset`                | 数値                                                                              | `1`                      | 小数桁数（例: `digits:2` → `2.50h`）                                                                  |
| `format`          | `*_reset_at`             | `auto`/`auto_tz`/`time`/`time_tz`/`datetime`/`datetime_tz`/`full`/`full_tz`/`iso` | `auto`                   | 日時フォーマット（`auto`=今日なら時刻のみ、別日なら`M/D HH:MM`）                                      |
| `tz`              | `*_reset_at`             | `local` / `utc`                                                                   | `local`                  | 表示タイムゾーン                                                                                      |
| `on-error`        | `5h_pct`, `7d_pct`, `*_reset`, `*_reset_at`, `cmd` | `hide` / `text(文字列)`                                               | （エラー文字列を表示）   | API エラーまたはコマンド失敗時の表示制御（`hide`=非表示、`text(...)`=カスタム文字列を表示）          |
| `timeout`         | `cmd`                    | 数値（秒）                                                                        | `2`                      | コマンド実行のタイムアウト秒数。超過時は空文字を返す                                                  |
| `hide-under`      | `ctx_pct`, `5h_pct`, `7d_pct`               | 数値（%）                                                                  | —                        | 使用率が N% 未満の場合に非表示にする（データ欠損時も非表示）。例: `hide-under:70`                    |
| `hide-under-sec`  | `duration`, `api_duration`                  | 数値（秒）                                                                 | —                        | 経過時間が N 秒未満の場合に非表示にする。例: `hide-under-sec:60`                                     |
| `hide-zero`       | `cost`, `lines_added`, `lines_removed`      | `1`                                                                        | —                        | 値がちょうど 0 の場合に非表示にする                                                                  |
| `digits`          | `cost`                                      | 数値                                                                       | `2`                      | コスト金額の小数桁数（例: `digits:3` → `$0.421`）                                                    |
| `text`            | `exceeds_200k`                              | 文字列                                                                     | `200k+`                  | インジケータ発火時に表示するカスタムラベル                                                          |
| `hide-if`         | `branch`, `branch_dirty`, `model`, `cwd`, `cwd_short`, `cwd_full`, `repo`, `repo_owner`, `repo_full`, `effort`, `output_style`, `vim_mode` | 文字列                              | —                        | 解決後の値が指定文字列と完全一致（大文字小文字区別）する場合に非表示にする                           |
| `dirty-suffix`    | `branch`, `branch_dirty` | 文字列                                                                            | `*` / `""`               | dirty 時に付加するサフィックス（`branch_dirty` デフォルト: `*`、`branch` はデフォルト空でオプトイン） |
| `dirty-color`     | `branch`, `branch_dirty` | 色名                                                                              | `color` にフォールバック | dirty 時の色                                                                                          |
| `haiku-color`     | `model`                  | 色名                                                                              | `amber`                  | Haiku モデル時の色                                                                                    |
| `sonnet-color`    | `model`                  | 色名                                                                              | `sky_blue`               | Sonnet モデル時の色                                                                                   |
| `opus-color`      | `model`                  | 色名                                                                              | `pink`                   | Opus モデル時の色                                                                                     |
| `<level>-color`   | `effort`                 | 色名                                                                              | レベル別デフォルト（上記参照） | effort のレベル別色上書き。例: `low-color:cyan`, `max-color:magenta`                            |

### 使用可能な色名

`red`, `green`, `yellow`, `cyan`, `blue`, `magenta`, `gray`, `light_gray`,
`sky_blue`, `pink`, `amber`, `purple`, `bold`, `bold_yellow`

### 設定例

![examples](.github/assets/examples.png)

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

# リセット日時を表示（絶対時刻）
export CLAUDE_NANO_LINE_FORMAT="{5h_pct} {5h_reset_at} {7d_pct} {7d_reset_at} {model}"

# リセット日時をタイムゾーン付きで表示
export CLAUDE_NANO_LINE_FORMAT="{5h_pct} {5h_reset_at|format:time_tz} {7d_pct} {7d_reset_at|format:datetime_tz} {model}"

# UTC で表示
export CLAUDE_NANO_LINE_FORMAT="{5h_reset_at|tz:utc,format:auto_tz} {7d_reset_at|tz:utc,format:full}"

# コンテキストのトークン数表示（モデル名から推定）
export CLAUDE_NANO_LINE_FORMAT="{ctx_pct} {ctx_used_tokens}/{ctx_total_tokens} {model}"

# Git dirty 表示（未コミット変更があると "main*" と表示）
export CLAUDE_NANO_LINE_FORMAT="{5h_pct} {model} {cwd} {branch_dirty}"

# dirty 時に色を変える（clean: cyan、dirty: yellow）
export CLAUDE_NANO_LINE_FORMAT="{5h_pct} {model} {cwd} {branch_dirty|color:cyan,dirty-color:yellow}"

# {branch} にオプトインで dirty マーカーを付加
export CLAUDE_NANO_LINE_FORMAT="{5h_pct} {model} {cwd} {branch|dirty-suffix:!,dirty-color:red}"

# API エラー時に項目を非表示（サイレントフォールバック）
export CLAUDE_NANO_LINE_FORMAT="{5h_pct|on-error:hide} {model}"

# API エラー時にカスタムテキストを表示
export CLAUDE_NANO_LINE_FORMAT="{5h_pct|on-error:text(N/A)} {model}"

# 使用率が 70% を超えたときだけ表示
export CLAUDE_NANO_LINE_FORMAT="{5h_pct|hide-under:70} {7d_pct|hide-under:70} {model}"

# main ブランチ以外のときだけブランチ名を表示
export CLAUDE_NANO_LINE_FORMAT="{model} {cwd} {branch|hide-if:main}"

# ディレクトリ名の代わりにリポジトリ名を表示（git worktree でも変わらない）
export CLAUDE_NANO_LINE_FORMAT="{5h_pct} {model} {repo|color:sky_blue} {branch_dirty|color:cyan}"

# リポジトリ名を表示し、ディレクトリ名が指定した文字列（例では ClaudeNanoLine）と
# 一致するときだけ隠す
export CLAUDE_NANO_LINE_FORMAT="{repo|color:sky_blue} {cwd|hide-if:ClaudeNanoLine,prefix:(,suffix:)} {branch_dirty}"

# main ブランチでは非表示・使用率 80% 未満は非表示
export CLAUDE_NANO_LINE_FORMAT="{5h_pct|hide-under:80} {model} {branch|hide-if:main}"

# 現在時刻を cyan で表示（シンプルなコマンド、パイプなし）
export CLAUDE_NANO_LINE_FORMAT="{cmd:date +%H:%M|color:cyan} {model}"

# コマンド内にダブルクォートが含まれる場合は、外側をシングルクォートで囲む
export CLAUDE_NANO_LINE_FORMAT='{cmd:date "+%Y-%m-%d %H:%M"|color:cyan} {model}'

# ロードアベレージをパイプで加工（| を含むコマンドはバッククォートで囲む）
export CLAUDE_NANO_LINE_FORMAT="{cmd:\`uptime | awk '{print \$NF}'\`|color:yellow} {model}"

# コマンド失敗時にフォールバックテキストを表示
export CLAUDE_NANO_LINE_FORMAT="{cmd:false|on-error:text(N/A)} {model}"

# 認証リトライ挙動をログで確認（401対策）
tail -n 20 "${XDG_STATE_HOME:-$HOME/.local/state}/claude-nano-line/claude-usage-api.log" | rg "error:auth|info:forcing one auth retry|info:token changed"
```

`~/.zprofile` や `~/.bashrc` に `export` 行を追加すれば常時有効になります。

## トラブルシューティング

### API 使用率が `[5h] --%` / `[7d] --%` と表示される

- **トークン未取得**: Claude Code で一度ログインしてください。macOS はキーチェーン、Windows/Linux は
  `~/.claude/.credentials.json` にトークンが保存されます。
- **ネットワーク**: API への接続に失敗している可能性があります。ファイアウォールやプロキシ設定を確認してください。
- **401 からの復旧挙動**: 認証エラー時はエラーをキャッシュしつつ、同一トークンでも 1 回だけ強制再試行します。
  それでも失敗する場合は Claude Code で再ログインし、OS に応じた保存先を確認してください（macOS は
  Keychain、Windows/Linux は `~/.claude/.credentials.json`）。トークンが古いままなら、
  Claude Code で再ログインして更新してください。

### `Token Expired (/login)` と表示される

OAuth アクセストークンが期限切れです（トークンの有効期間は 8 時間）。Claude Code で
`/login` を実行して新しいトークンを取得してください。スクリプトは API を呼び出す前に
`expiresAt` フィールドを確認し、不要な 401 リクエストを回避します。

### 認証切れが頻発する場合の自動修復（macOS 限定・opt-in）

Claude Code の認証が頻繁に切れる場合、環境変数 `CLAUDE_NANO_LINE_AUTO_FIX_AUTH=1`
を設定してください。ClaudeNanoLine が *確定した* 認証障害（組み込みの強制再試行後も
続く 401、または Keychain のトークンが 1 時間を超えて期限切れのまま）を検知すると、
`security delete-generic-password -s 'Claude Code-credentials'` を自動実行して
古い認証エントリを削除した上で、同一プロセス内で credentials file などの別トークンによる即時リトライ（無ければ再ログイン）を試みます。

- **macOS 限定**かつ**既定では無効**です。通常のトークン期限切れでは発火しません。
- このコマンドは**破壊的**です。Keychain の認証エントリを削除するため、実行後は
  `/login` での**再ログインが必要**になります。
- 連打を防ぐため、コマンドの再実行は**最短 1 時間間隔**です（マーカー
  `$XDG_STATE_HOME/claude-nano-line/auth-fix.marker` で管理）。実行のたびに
  API ログ（`claude-usage-api.log`）へ `info:auth-fix ...` として記録されます。

`~/.claude/settings.json` の `env` ブロックで有効化します:

```json
{
  "env": {
    "CLAUDE_NANO_LINE_AUTO_FIX_AUTH": "1"
  }
}
```

### `Timeout` と表示される

API リクエストがタイムアウトしました。ネットワーク状況を確認し、数分後に再試行してください（360 秒キャッシュ後に完了後に自動で再取得されます）。

### `Usage API Rate Limit` と表示される

API のレート制限に達しました。しばらく待つと自動で復旧します。

### ログの確認

API 呼び出しの詳細は `$XDG_STATE_HOME/claude-nano-line/claude-usage-api.log`（デフォルト:
`~/.local/state/claude-nano-line/`）に記録されます。問題の切り分けに役立ちます。

### Claude Code のメモリ使用量が異常に増える（macOS）

長時間のセッションなどで Claude Code プロセスの RSS（常駐セットサイズ）が異常に大きくなり、マシン全体が重くなったり実質フリーズしたりすることがあります。原因は不明ですが、カスタムのステータスラインを使っていると起きやすくなるようです。症状の見分け方、手動での対処、`launchd` を使ったウォッチドッグによる自動停止の例などは、次の記事を参考にしてください: [Claude Code のメモリ暴走で Mac がフリーズする前に自動で止める](https://zenn.dev/happy_onigiri/articles/9ae9080ba5eb88)

## コントリビュート

Issue や Pull Request を歓迎します。バグ報告、機能提案、ドキュメントの改善など、どんな貢献でもお気軽にどうぞ。
