# Changelog

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
