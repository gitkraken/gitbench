## ADDED Requirements

### Requirement: Profiles declare credential environment variable names
Model profiles that require API credentials SHALL declare the environment variable name with `api_key_env`. GitBench SHALL resolve the named variable from the process environment after loading supported environment files and SHALL pass the resolved secret only through runtime data structures.

#### Scenario: Profile resolves API key from named environment variable
- **WHEN** a profile contains `"api_key_env": "OPENROUTER_API_KEY"` and `OPENROUTER_API_KEY` is set in the process environment
- **THEN** resolving the profile returns a runtime `api_key` value equal to the environment variable value

#### Scenario: Profile preserves credential variable name for validation
- **WHEN** a profile contains `"api_key_env": "OPENAI_API_KEY"`
- **THEN** resolving the profile records the source variable name for missing-credential validation and user-facing error messages

#### Scenario: Profile without credentials remains valid for local provider
- **WHEN** a profile does not contain `api_key_env` and uses a local provider such as Ollama
- **THEN** resolving the profile does not require or synthesize an API key

### Requirement: Project dotenv file is loaded before credential resolution
GitBench SHALL load variables from a project `.env` file before resolving profile credentials. Existing process environment variables MUST take precedence over values from `.env`.

#### Scenario: Credential resolves from dotenv file
- **WHEN** `.env` contains `OPENAI_API_KEY=sk-from-dotenv` and a profile references `"api_key_env": "OPENAI_API_KEY"`
- **THEN** resolving the profile uses `sk-from-dotenv` as the runtime API key

#### Scenario: Shell environment takes precedence over dotenv file
- **WHEN** the process environment contains `OPENAI_API_KEY=sk-from-shell` and `.env` contains `OPENAI_API_KEY=sk-from-dotenv`
- **THEN** resolving the profile uses `sk-from-shell` as the runtime API key

#### Scenario: Missing dotenv file is allowed
- **WHEN** no `.env` file exists
- **THEN** GitBench continues loading config and resolving credentials from the existing process environment

### Requirement: Literal API keys are invalid in profile config
GitBench SHALL reject model profiles that contain a literal `api_key` field in persisted config. The failure message MUST identify the unsupported field and direct the user to use `.env` or the shell environment with `api_key_env`.

#### Scenario: Profile contains literal api_key
- **WHEN** a config profile contains `"api_key": "sk-secret"`
- **THEN** profile resolution fails before any model API call is attempted

#### Scenario: Profile contains both api_key and api_key_env
- **WHEN** a config profile contains both `"api_key": "sk-secret"` and `"api_key_env": "OPENAI_API_KEY"`
- **THEN** profile resolution fails because literal `api_key` is not supported

### Requirement: Example env file documents expected secrets safely
The repository SHALL include a committed `.env.example` that lists supported API key variable names with empty or placeholder values and SHALL NOT include real secrets.

#### Scenario: User copies env example for local setup
- **WHEN** a user opens `.env.example`
- **THEN** it shows variable names such as `OPENAI_API_KEY` and `OPENROUTER_API_KEY` without containing usable credential values

#### Scenario: Local dotenv file remains uncommitted
- **WHEN** a user creates `.env` with real API key values
- **THEN** the repository ignore rules prevent `.env` from being tracked by default

### Requirement: User-facing profile output hides credential values
User-facing config and profile listing output SHALL display credential variable names but MUST NOT display resolved API key values.

#### Scenario: Profiles command shows credential source
- **WHEN** a profile contains `"api_key_env": "OPENROUTER_API_KEY"`
- **THEN** the profiles command displays `api_key_env=OPENROUTER_API_KEY`

#### Scenario: Profiles command does not show resolved secret
- **WHEN** `OPENROUTER_API_KEY` is set to a real secret and profiles are listed
- **THEN** the secret value is not included in command output
