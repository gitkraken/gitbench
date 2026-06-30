## ADDED Requirements

### Requirement: Fixture setup disables Git signing
Benchmark fixture setup commands SHALL run in a Git environment where commit signing and tag signing are disabled, regardless of the user's global Git signing configuration.

#### Scenario: Global commit signing does not break fixture setup
- **WHEN** the user's Git configuration enables `commit.gpgsign`
- **AND** a fixture setup command creates a commit without configuring a signing key
- **THEN** fixture setup succeeds without attempting to sign the commit

#### Scenario: Nested fixture setup repositories inherit unsigned Git behavior
- **WHEN** a fixture setup command creates a nested repository and commits inside that nested repository
- **AND** the user's Git configuration enables `commit.gpgsign`
- **THEN** the nested repository commit succeeds without attempting to sign

### Requirement: Stateful benchmark command execution disables Git signing
Benchmarks that execute model-provided Git commands during scoring SHALL run those commands in a Git environment where commit signing and tag signing are disabled.

#### Scenario: Annotated tag command is not forced to sign
- **WHEN** the user's Git configuration enables `tag.gpgSign`
- **AND** a stateful benchmark executes model output `git tag -a v1.0 -m release`
- **THEN** the command succeeds as an annotated tag without requiring a signing key

#### Scenario: Model-executed commit command is not forced to sign
- **WHEN** the user's Git configuration enables `commit.gpgsign`
- **AND** a stateful benchmark executes model output that creates a commit
- **THEN** the command succeeds without attempting to sign the commit

### Requirement: Benchmark Git environment preserves unrelated Git configuration
The benchmark Git environment SHALL disable signing without discarding unrelated user or system Git configuration.

#### Scenario: Default branch configuration remains available
- **WHEN** user or system Git configuration sets `init.defaultBranch` to `main`
- **AND** fixture setup initializes a new repository
- **THEN** the initialized repository uses `main` according to that Git configuration

#### Scenario: Existing environment Git config entries are preserved
- **WHEN** the process environment already contains Git config entries unrelated to signing
- **THEN** benchmark Git commands preserve those entries while applying unsigned commit and tag behavior
