## 1. Environment Loading

- [x] 1.1 Add `python-dotenv` as a runtime dependency.
- [x] 1.2 Add a config-layer helper that loads the project `.env` file without overriding existing process environment values.
- [x] 1.3 Ensure CLI and doctor flows load `.env` before resolving profiles or validating missing credential variables.

## 2. Profile Credential Validation

- [x] 2.1 Update profile resolution to reject persisted `api_key` fields with a clear migration error.
- [x] 2.2 Preserve `api_key_env` resolution into runtime-only `api_key` values after dotenv loading.
- [x] 2.3 Ensure profile listing output displays `api_key_env=<name>` and never displays resolved secret values.

## 3. Example And Documentation

- [x] 3.1 Add `.env.example` with empty placeholder entries for common provider keys.
- [x] 3.2 Confirm `.env` is ignored by default.
- [x] 3.3 Update README configuration docs to show `.env` plus `api_key_env` and remove literal `api_key` guidance.
- [x] 3.4 Update any package metadata or generated docs that describe config profile credential behavior.

## 4. Tests And Verification

- [x] 4.1 Add config tests for resolving keys from `.env`, preserving shell env precedence, and allowing missing `.env`.
- [x] 4.2 Add config tests that `api_key` and `api_key` plus `api_key_env` fail before model calls.
- [x] 4.3 Add CLI/profile tests that missing `api_key_env` values produce the expected user-facing error.
- [x] 4.4 Run targeted Python tests for config and CLI credential behavior.
