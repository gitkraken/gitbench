## MODIFIED Requirements

### Requirement: Known brittle fixtures are corrected
Fixtures with known incorrect, ambiguous, or brittle expectations SHALL be corrected so valid answers pass, objectively wrong expectations are removed, and the repository state identifies one deterministic expected answer.

#### Scenario: Submodule list accepts status form
- **WHEN** the submodule listing fixture asks for the command to list configured submodules
- **THEN** both `git submodule` and `git submodule status` are accepted as correct

#### Scenario: Full hash fixture expects a hash
- **WHEN** the `git_show/f008` fixture asks for the full SHA hash of the commit with message `Second commit`
- **THEN** the fixture no longer expects the literal text `Second commit`

#### Scenario: Broken import has one introducing commit
- **WHEN** `blame_forensics/f010` asks which commit introduced an import from the nonexistent `helpers` module
- **THEN** exactly one commit SHALL introduce the broken import and the current broken line SHALL blame to `Update import path`

#### Scenario: Later formatter commits do not duplicate the defect
- **WHEN** later commits in `blame_forensics/f010` add or modify a formatter import
- **THEN** those commits SHALL use an existing module and SHALL preserve blame for the broken helper import on `Update import path`
