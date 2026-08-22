# Usage data, credentials, and cache

Read this guide when changing Anthropic Usage API calls, credential discovery,
caching, TLS behavior, error rendering inputs, or macOS authentication repair.

## Entry points

Start cache and credential orchestration changes in `get_usage_data()`. Start
HTTP, response normalization, and API error mapping changes in `fetch_usage()`.
Both renderers consume the resulting `usage` mapping.

On macOS, `get_oauth_token()` checks the `Claude Code-credentials` Keychain
entry first. The credentials-file fallback supports other platforms and auth
repair. API results and API error states are cached under the XDG cache path;
diagnostic logs and the auth-repair marker use the XDG state path.

## Behavioral invariants

- Runtime code must never log or cache a raw OAuth token. `_token_hash()` is the
  comparison identifier used to detect a changed credential.
- Keep API, cache, and credential failures from escaping into `main()`;
  represent user-visible API failures with `api_error`. Renderers own the
  fallback and `on-error` behavior.
- Auth-error cache entries may be bypassed when the token changes, when a token
  appears after a no-token result, or for the one forced retry recorded by
  `_auth_retry_done`. Preserve these distinctions when changing cache logic.
- Cached percentages are overridden to zero after their recorded reset time is
  crossed, even while the rest of the cache entry remains valid.
- macOS Keychain deletion is opt-in, requires a confirmed/stuck auth failure,
  and is cooldown-protected. The marker path is derived from `LOG_DIR` at call
  time so tests that replace `LOG_DIR` remain isolated.
- Cache writes use a temporary file followed by `os.replace()`. Preserve atomic
  replacement because Claude Code can invoke the status line repeatedly.
- TLS uses the system trust store first and may use `certifi` only as an
  optional fallback.

## Testing boundaries

Patch the imported module (`cnl`) rather than contacting the network, Keychain,
credentials file, or real XDG directories. Cover cache-hit and cache-miss paths
separately from `fetch_usage()` response parsing. Authentication changes should
also cover repeated 401s, token replacement, opt-in state, platform checks, and
cooldown behavior.

Keep cache and log locations isolated in temporary directories. Because the
auth-repair marker follows `LOG_DIR`, replacing that directory isolates all
auth-repair state as well.
