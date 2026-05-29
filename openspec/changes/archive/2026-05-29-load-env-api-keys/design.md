## Context

GitBench profile config already separates most provider settings from runtime credentials by allowing profiles to name an `api_key_env` variable. The resolver then reads that variable from `os.environ` and passes the resolved value to OpenAI-compatible adapters.

Two gaps remain. First, GitBench does not load a local `.env` file, so users must export variables manually before every run or rely on shell-specific setup. Second, config still accepts literal `api_key` values, which creates a direct path for secrets to land in `gitbench.json`, `.gitbench.json`, or `~/.gitbench.json`.

## Goals / Non-Goals

**Goals:**
- Load a project `.env` file before resolving profile credentials.
- Preserve the existing `api_key_env` config field.
- Reject literal `api_key` values in profile config.
- Provide a committed `.env.example` with safe placeholder variable names.
- Keep runtime adapters receiving an `api_key` value internally so adapter APIs do not need to change.
- Make missing credential errors happen before real model runs start.

**Non-Goals:**
- Rename profile config fields to camelCase.
- Introduce a full settings framework for all GitBench options.
- Manage provider-specific secret validation beyond checking whether the named env var has a value.
- Store secrets in result files, logs, profile listings, or OpenSpec artifacts.

## Decisions

### Use `python-dotenv` For `.env` Loading

GitBench will add `python-dotenv` as a runtime dependency and load `.env` before config profile resolution needs credentials. The loader will use dotenv's default non-overriding behavior so already-exported shell environment variables remain authoritative.

Rationale: GitBench already has JSON config and does not need a full typed settings system. `python-dotenv` solves the exact local development problem while keeping the current config model.

Alternative considered: implement a small `.env` parser in GitBench. This avoids a dependency but is easy to get subtly wrong around quoting, comments, and escaping.

Alternative considered: use Pydantic settings. This would be heavier than the problem requires and would pressure unrelated config into a new model.

### Keep `api_key_env` As The Public Config Field

Profiles will continue to declare credentials by naming an environment variable with `api_key_env`. The resolver will read the named variable from the process environment after `.env` loading and expose the actual value only in the resolved runtime profile dict.

Rationale: existing docs, tests, and config style use snake_case fields such as `base_url`, `api_key_env`, and `max_concurrent_requests`. Keeping `api_key_env` avoids mixed config naming and keeps this change scoped.

Alternative considered: rename to `apiKeyEnvVar`. This is explicit but inconsistent with the rest of GitBench's JSON config.

### Reject Literal `api_key` In Config

Profile resolution will fail fast when a profile includes `api_key`. The error should identify the profile and tell the user to move the secret to `.env` or their shell environment, then set `api_key_env` to the variable name.

Rationale: this project has one user today, so a clean breaking change is preferable to carrying a knowingly unsafe compatibility path.

Alternative considered: warn for one release before erroring. That is useful for broad public usage but adds complexity and leaves the secret footgun in place.

### Keep Runtime Adapter Boundaries Stable

The config layer may still return a resolved `api_key` in memory, and `get_model_client()` may keep accepting an `api_key` argument. The banned surface is persisted profile config, not internal runtime data flow.

Rationale: adapters need the secret value to call provider APIs. Changing the adapter boundary to accept env var names would push config concerns into model transport code and complicate tests.

Alternative considered: pass `api_key_env` down to the adapter and have adapters read env vars. That spreads credential resolution across layers and makes provider-independent validation harder.

## Risks / Trade-offs

- [Risk] Loading `.env` from the wrong directory could surprise users running GitBench from nested paths. -> Mitigation: follow GitBench's existing config search expectations and document where `.env` is loaded from.
- [Risk] Users with both shell env and `.env` values may expect `.env` to win. -> Mitigation: document that existing environment values take precedence, matching common dotenv behavior.
- [Risk] Literal `api_key` rejection breaks old local config. -> Mitigation: provide a direct error message and `.env.example` migration path.
- [Risk] Profile listing could accidentally reveal resolved secret values. -> Mitigation: display only `api_key_env=<name>` and never print resolved API key values.

## Migration Plan

1. Add `python-dotenv` to runtime dependencies.
2. Add `.env.example` with non-secret placeholders for supported provider key names.
3. Load `.env` before config profile credential resolution in CLI and doctor paths.
4. Reject `api_key` fields during profile resolution.
5. Update README examples to show `.env` plus `api_key_env`.
6. Update tests for `.env` loading, shell env precedence, missing variable errors, and literal `api_key` rejection.

Rollback is straightforward: remove dotenv loading and restore literal `api_key` support. No persisted result schema changes are involved.
