# Changelog

## [0.4.0](https://github.com/HappyOnigiri/ClaudeNanoLine/compare/ClaudeCodeStatusline-v0.3.0...ClaudeCodeStatusline-v0.4.0) (2026-03-20)


### Features

* **claude-nano-line:** 5h_reset_at / 7d_reset_at プレースホルダーを追加 ([c7187c8](https://github.com/HappyOnigiri/ClaudeNanoLine/commit/c7187c89bad96a3ab64b63940969a4e949bbb0f0))
* **claude-nano-line:** auto フォーマットで1日以上2日未満の場合に XdXh 形式で表示 ([8d46fce](https://github.com/HappyOnigiri/ClaudeNanoLine/commit/8d46fce4dad4e21be5ddcb64cc6f50a34fd64b9d))
* **claude-nano-line:** Git dirty 状態の可視化を追加 ([ec9c015](https://github.com/HappyOnigiri/ClaudeNanoLine/commit/ec9c0153b29e1127c4c4ba04f6cc6dfae23cee5b))
* **claude-nano-line:** コンテキストウィンドウのトークン数絶対値表示を追加 ([394556c](https://github.com/HappyOnigiri/ClaudeNanoLine/commit/394556c1ed0cfccbb5f2a43d0a702ad9bc3b93fc))
* **claude-nano-line:** テーマプリセット機能を追加（CLAUDE_NANO_LINE_THEME 環境変数） ([a7b6e0b](https://github.com/HappyOnigiri/ClaudeNanoLine/commit/a7b6e0b0c372fb5b4a2f03cfac3b54088403f6d4))
* curl APIリクエストにUser-AgentとAnthropicバージョンヘッダーを追加 ([9a19f43](https://github.com/HappyOnigiri/ClaudeNanoLine/commit/9a19f43b16af3f71765913f0b6cf71d8ec30270c))
* **root:** bash+Python ハイブリッドを純 Python スクリプトに書き換え（jq/curl 依存排除・フレキシブルフォーマット対応） ([951a7b0](https://github.com/HappyOnigiri/ClaudeNanoLine/commit/951a7b036035ff6e3294269312d6a427c9566bd6))
* **root:** Windows/Linux向けに認証情報ファイルからトークン取得するフォールバックを追加 ([65e1c07](https://github.com/HappyOnigiri/ClaudeNanoLine/commit/65e1c078f5c91fc339d5241baa95180ce03ad017))
* **root:** ステータスラインの機能強化（モデル別色・エラー処理・レイアウト改善） ([b4b4e14](https://github.com/HappyOnigiri/ClaudeNanoLine/commit/b4b4e1490ec3a392975e09795754f8ce577a18d2))
* **scripts:** make demo コマンドを追加（全テーマ・全 Example を一括確認） ([d6682af](https://github.com/HappyOnigiri/ClaudeNanoLine/commit/d6682af18eb95b8596daadf19fc348116b66d047))
* **statusline:** ステータスラインの機能強化（モデル別色・クロスプラットフォーム対応・APIヘッダー改善） ([732f447](https://github.com/HappyOnigiri/ClaudeNanoLine/commit/732f44705b66cc1167b32ae315e568969e55354f))


### Bug Fixes

* add clean target to remove tmp/ directory ([d2333d7](https://github.com/HappyOnigiri/ClaudeNanoLine/commit/d2333d7e1f9f73a2b392986061413546b8fae9b3))
* **ci:** README.md を mdformat 対象から除外し GFM テーブル崩れを防ぐ ([70c324c](https://github.com/HappyOnigiri/ClaudeNanoLine/commit/70c324c2b23ea8f4d4e716d86bdef89ac0190d76))
* **claude-nano-line.py:** get_threshold_color で不正な閾値に対し ValueError をキャッチしデフォルト値にフォールバック ([b403385](https://github.com/HappyOnigiri/ClaudeNanoLine/commit/b403385a44c4a7c8dc5840f887e208ffabfa1c35))
* **claude-nano-line.py:** HTTP 429 を rate-limit として正しく処理 ([534cbb6](https://github.com/HappyOnigiri/ClaudeNanoLine/commit/534cbb650f611a32b4662c030c4ae60ab8a853d7))
* **claude-nano-line.py:** workspace/model/context_window が null の場合の None.get() クラッシュを修正 ([8238a34](https://github.com/HappyOnigiri/ClaudeNanoLine/commit/8238a34acd2e24998e9de06bdc78bd2c88d46570))
* **claude-nano-line:** add from __future__ import annotations for Python 3.9 compatibility ([2633a05](https://github.com/HappyOnigiri/ClaudeNanoLine/commit/2633a05d58bf2956cb3fc7ef9d6c5ede64013a0a))
* **claude-nano-line:** digits オプションに無効な値が渡された場合のクラッシュを修正 ([be2c40d](https://github.com/HappyOnigiri/ClaudeNanoLine/commit/be2c40d15f453c5eb95d629101e7bc3cb9df1492))
* **claude-nano-line:** fmt_reset_time_v2 で digits に負値が渡された場合の無効フォーマット文字列を修正 ([84751fe](https://github.com/HappyOnigiri/ClaudeNanoLine/commit/84751fe37824fbe38f59cc21ef7087e0dd9c2175))
* **claude-nano-line:** increase GLOBAL_TIMEOUT to 20s to cover full serial path ([59978e5](https://github.com/HappyOnigiri/ClaudeNanoLine/commit/59978e53e56cef29b3d79b2c2d92434726a81256))
* **claude-nano-line:** removesuffix を Python 3.7 互換の文字列スライスに置き換え ([a98b2f2](https://github.com/HappyOnigiri/ClaudeNanoLine/commit/a98b2f212a0d5d929e464686e4b490520f07fa8b))
* **claude-nano-line:** stdin read をスレッド+キューに置き換えて STDIN_TIMEOUT を確実に適用 ([9568ebd](https://github.com/HappyOnigiri/ClaudeNanoLine/commit/9568ebd1e6a6da53fbab8e37b769328f44a3a623))
* **claude-nano-line:** strftime の %-m フラグを Windows 互換のフォーマットに置き換え ([6c363b3](https://github.com/HappyOnigiri/ClaudeNanoLine/commit/6c363b30c6de53c408825eb44ef51437c5b1c665))
* **claude-nano-line:** unit=dh で h が丸めにより 24 以上になる境界値バグを修正 ([016fc0e](https://github.com/HappyOnigiri/ClaudeNanoLine/commit/016fc0e64f7e71927701d9d78e98398f302d41a9))
* **claude-nano-line:** XDG 環境変数の相対パスを無視してデフォルトにフォールバック ([8041003](https://github.com/HappyOnigiri/ClaudeNanoLine/commit/80410039b67c4d626b399685f49eafb734c9d719))
* **claude-nano-line:** グローバルタイムアウトと stdin タイムアウトを追加してプロセスの残留を防止 ([9c706cb](https://github.com/HappyOnigiri/ClaudeNanoLine/commit/9c706cb223c5053bc7e2b1eaeffd4e43eb23bc52))
* remove undeclared targets from .PHONY ([94fdc94](https://github.com/HappyOnigiri/ClaudeNanoLine/commit/94fdc9480134cdc18402232e80040a624990dc96))
* **setup.sh:** STATUS_LINE_ENTRY を環境変数経由で Python に渡し JSON 構文エラーを回避 ([d5ae408](https://github.com/HappyOnigiri/ClaudeNanoLine/commit/d5ae4087d5d456572e1b91df14f83ed7927c6d82))
* **setup.sh:** statusLine を深いマージで更新し既存サブキーを保持 ([e774a38](https://github.com/HappyOnigiri/ClaudeNanoLine/commit/e774a38c0b9bce21b47cba46857a993c5bbb2990))
* **statusline:** CodeRabbitレビュー対応（Python最適化・変数宣言・未使用変数削除） ([e7a2151](https://github.com/HappyOnigiri/ClaudeNanoLine/commit/e7a21512ab295b1ef9ebb16fffd7f0ddf80ceea7))
* **statusline:** Pythonバージョンチェック強化とキャッシュ書き込みの原子化 ([795a4e4](https://github.com/HappyOnigiri/ClaudeNanoLine/commit/795a4e4081f083ec16c35c26fe592bc0d5f6ce3c))
* **statusline:** Python互換性・安全性・APIフォールバックの改善 ([a549715](https://github.com/HappyOnigiri/ClaudeNanoLine/commit/a549715662847d4a7910db729e74929e6bcf264c))

## [0.3.0](https://github.com/HappyOnigiri/ClaudeNanoLine/compare/ClaudeCodeStatusline-v0.2.0...ClaudeCodeStatusline-v0.3.0) (2026-03-18)


### Features

* **claude-nano-line:** auto フォーマットで1日以上2日未満の場合に XdXh 形式で表示 ([8d46fce](https://github.com/HappyOnigiri/ClaudeNanoLine/commit/8d46fce4dad4e21be5ddcb64cc6f50a34fd64b9d))
* **root:** bash+Python ハイブリッドを純 Python スクリプトに書き換え（jq/curl 依存排除・フレキシブルフォーマット対応） ([951a7b0](https://github.com/HappyOnigiri/ClaudeNanoLine/commit/951a7b036035ff6e3294269312d6a427c9566bd6))


### Bug Fixes

* **claude-nano-line.py:** get_threshold_color で不正な閾値に対し ValueError をキャッチしデフォルト値にフォールバック ([b403385](https://github.com/HappyOnigiri/ClaudeNanoLine/commit/b403385a44c4a7c8dc5840f887e208ffabfa1c35))
* **claude-nano-line.py:** HTTP 429 を rate-limit として正しく処理 ([534cbb6](https://github.com/HappyOnigiri/ClaudeNanoLine/commit/534cbb650f611a32b4662c030c4ae60ab8a853d7))
* **claude-nano-line.py:** workspace/model/context_window が null の場合の None.get() クラッシュを修正 ([8238a34](https://github.com/HappyOnigiri/ClaudeNanoLine/commit/8238a34acd2e24998e9de06bdc78bd2c88d46570))
* **claude-nano-line:** digits オプションに無効な値が渡された場合のクラッシュを修正 ([be2c40d](https://github.com/HappyOnigiri/ClaudeNanoLine/commit/be2c40d15f453c5eb95d629101e7bc3cb9df1492))
* **claude-nano-line:** fmt_reset_time_v2 で digits に負値が渡された場合の無効フォーマット文字列を修正 ([84751fe](https://github.com/HappyOnigiri/ClaudeNanoLine/commit/84751fe37824fbe38f59cc21ef7087e0dd9c2175))
* **claude-nano-line:** unit=dh で h が丸めにより 24 以上になる境界値バグを修正 ([016fc0e](https://github.com/HappyOnigiri/ClaudeNanoLine/commit/016fc0e64f7e71927701d9d78e98398f302d41a9))
* **setup.sh:** STATUS_LINE_ENTRY を環境変数経由で Python に渡し JSON 構文エラーを回避 ([d5ae408](https://github.com/HappyOnigiri/ClaudeNanoLine/commit/d5ae4087d5d456572e1b91df14f83ed7927c6d82))
* **setup.sh:** statusLine を深いマージで更新し既存サブキーを保持 ([e774a38](https://github.com/HappyOnigiri/ClaudeNanoLine/commit/e774a38c0b9bce21b47cba46857a993c5bbb2990))

## [0.2.0](https://github.com/HappyOnigiri/ClaudeCodeStatusline/compare/ClaudeCodeStatusline-v0.1.0...ClaudeCodeStatusline-v0.2.0) (2026-03-13)


### Features

* curl APIリクエストにUser-AgentとAnthropicバージョンヘッダーを追加 ([9a19f43](https://github.com/HappyOnigiri/ClaudeCodeStatusline/commit/9a19f43b16af3f71765913f0b6cf71d8ec30270c))
* **root:** Windows/Linux向けに認証情報ファイルからトークン取得するフォールバックを追加 ([65e1c07](https://github.com/HappyOnigiri/ClaudeCodeStatusline/commit/65e1c078f5c91fc339d5241baa95180ce03ad017))
* **root:** ステータスラインの機能強化（モデル別色・エラー処理・レイアウト改善） ([b4b4e14](https://github.com/HappyOnigiri/ClaudeCodeStatusline/commit/b4b4e1490ec3a392975e09795754f8ce577a18d2))
* **statusline:** ステータスラインの機能強化（モデル別色・クロスプラットフォーム対応・APIヘッダー改善） ([732f447](https://github.com/HappyOnigiri/ClaudeCodeStatusline/commit/732f44705b66cc1167b32ae315e568969e55354f))


### Bug Fixes

* **statusline:** CodeRabbitレビュー対応（Python最適化・変数宣言・未使用変数削除） ([e7a2151](https://github.com/HappyOnigiri/ClaudeCodeStatusline/commit/e7a21512ab295b1ef9ebb16fffd7f0ddf80ceea7))
* **statusline:** Pythonバージョンチェック強化とキャッシュ書き込みの原子化 ([795a4e4](https://github.com/HappyOnigiri/ClaudeCodeStatusline/commit/795a4e4081f083ec16c35c26fe592bc0d5f6ce3c))
* **statusline:** Python互換性・安全性・APIフォールバックの改善 ([a549715](https://github.com/HappyOnigiri/ClaudeCodeStatusline/commit/a549715662847d4a7910db729e74929e6bcf264c))
