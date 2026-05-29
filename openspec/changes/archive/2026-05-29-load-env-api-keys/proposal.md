## Why

GitBench currently supports resolving profile API keys from environment variables, but it does not load a project `.env` file and still permits literal `api_key` secrets in JSON config. This makes local setup less clear and leaves an avoidable path for committing secrets.

## What Changes

- Load environment variables from a project `.env` file before resolving model profile credentials.
- Add a committed `.env.example` that documents expected API key variable names without containing secrets.
- Keep `api_key_env` as the supported profile field for naming the environment variable that contains a provider key.
- **BREAKING**: Reject literal `api_key` fields in `gitbench.json`, `.gitbench.json`, and `~/.gitbench.json`.
- Update README and profile listing behavior so users see env-var references, not secret values.

## Capabilities

### New Capabilities
- `profile-credential-resolution`: Defines how model profile credentials are declared, loaded from environment sources, validated, and exposed to runtime adapters.

### Modified Capabilities
- None.

## Impact

- Affected code: `gitbench/config.py`, CLI profile validation paths in `gitbench/cli.py`, package dependencies, and profile display output.
- Affected config: model profiles must use `api_key_env`; `api_key` is no longer accepted.
- Affected files: add `.env.example` and ensure `.env` remains ignored.
- Affected docs/tests: README configuration examples and config/CLI tests need coverage for dotenv loading, missing vars, and literal-secret rejection.
