# result-safety-doctoring Specification

## Purpose
TBD - created by archiving change add-result-safety-doctoring. Update Purpose after archive.
## Requirements
### Requirement: Dedicated result-safety configuration
The system SHALL accept an optional `result_safety.profile` configuration property that references an existing model profile used only for result-safety classification. The referenced profile MUST resolve to exactly one model.

#### Scenario: Valid safety profile
- **WHEN** `.gitbench.json` contains `result_safety.profile` referencing a profile with one configured model
- **THEN** GitBench resolves that profile using the existing provider and credential configuration
- **AND** uses the resolved model for result-safety reviews

#### Scenario: Missing safety profile
- **WHEN** `result_safety.profile` references a profile that does not exist
- **THEN** GitBench exits with a configuration error naming the missing profile

#### Scenario: Multi-model safety profile
- **WHEN** `result_safety.profile` references a profile containing zero or multiple models
- **THEN** GitBench exits with an error stating that result safety requires exactly one model

#### Scenario: Safety is not configured
- **WHEN** `.gitbench.json` has no `result_safety` section
- **THEN** existing run and report behavior remains unchanged

### Requirement: Strict NSFW classification contract
The result-safety reviewer SHALL classify model-generated content using a structured response with a decision of `allow` or `redact`. A redaction decision MUST use the reason code `inappropriate_nsfw_content`, and invalid reviewer responses SHALL be treated as review failures.

#### Scenario: Allowed content
- **WHEN** the reviewer returns a valid `allow` decision for a score
- **THEN** the score's generated content remains unchanged

#### Scenario: Inappropriate NSFW content
- **WHEN** the reviewer returns a valid `redact` decision with reason `inappropriate_nsfw_content`
- **THEN** the score is selected for comprehensive redaction

#### Scenario: Invalid reviewer response
- **WHEN** the reviewer returns empty, malformed, or out-of-contract data
- **THEN** the safety review fails
- **AND** GitBench does not treat the content as allowed

#### Scenario: Reviewer request failure
- **WHEN** the reviewer model request fails after configured adapter retries
- **THEN** the safety review fails closed
- **AND** no normal output artifact is written or modified

### Requirement: Complete generated-content review
The system SHALL review one canonical content bundle per fixture score containing `model_output`, assistant-role transcript content, `raw_structured_output`, deterministic serialization of `parsed_payload`, and retained `error` or `structured_error` diagnostics when those values are present. User-role transcript content, prompts, and expected answers MUST NOT be submitted as review content.

#### Scenario: Text-mode score
- **WHEN** a text-mode score contains `model_output` and an assistant transcript entry
- **THEN** both generated representations are included in the same safety-review unit

#### Scenario: Structured-mode score
- **WHEN** a structured-mode score contains `model_output`, `raw_structured_output`, or `parsed_payload`
- **THEN** every present generated representation is included in the same safety-review unit

#### Scenario: Duplicate generated bundle
- **WHEN** multiple scores in one safety-doctor operation produce the same canonical content hash
- **THEN** the reviewer is called once for that content
- **AND** the cached decision is applied to every matching score

### Requirement: Comprehensive deterministic redaction
When a score is classified for redaction, the system SHALL replace every stored model-generated representation in that score with `[Redacted - Reason: Inappropriate NSFW content]` or a structurally valid equivalent containing only that marker. The application, not the reviewer model, MUST author the replacement.

#### Scenario: Redact text-mode duplicates
- **WHEN** a text-mode score is classified for redaction
- **THEN** `model_output` is replaced with the fixed redaction marker
- **AND** every assistant-role transcript content value is replaced with the same marker
- **AND** user-role transcript entries remain unchanged

#### Scenario: Redact structured-output fields
- **WHEN** a structured-mode score is classified for redaction
- **THEN** `model_output` and `raw_structured_output` are replaced with the fixed marker
- **AND** `parsed_payload` no longer contains any original generated string
- **AND** the resulting payload remains JSON serializable

#### Scenario: Redact retained diagnostics
- **WHEN** a score is classified for redaction
- **AND** its `error` or `structured_error` field contains retained content
- **THEN** every non-empty diagnostic value is replaced with the fixed redaction marker

#### Scenario: Preserve evaluation fields
- **WHEN** a score is redacted
- **THEN** its pass/fail value, similarity, token counts, cost, timing, fixture metadata, and enclosing benchmark summaries remain unchanged

### Requirement: Auditable and idempotent safety metadata
The system SHALL attach score-level and artifact-level safety metadata that identifies the policy version, reviewer profile and model, review time, decision status, content hashes, and redaction counts without retaining original generated text.

#### Scenario: Clean reviewed score
- **WHEN** a score is reviewed and allowed
- **THEN** its safety metadata records an `allow` status and matching current-content hash

#### Scenario: Redacted reviewed score
- **WHEN** a score is redacted
- **THEN** its safety metadata records `redacted`, the reason code, the pre-review content hash, and the current redacted-content hash

#### Scenario: Unchanged score reviewed again
- **WHEN** a score already has current-policy safety metadata and its current content hash matches
- **THEN** the safety doctor skips the reviewer call for that score

#### Scenario: Reviewed score content changes
- **WHEN** a score's current content hash does not match its recorded safety metadata
- **THEN** the score is reviewed again before the artifact can be marked complete

### Requirement: Original artifact backup
Before replacing an existing artifact that contains one or more redactions, the system SHALL copy the complete original artifact into `gitbench-results-nsfw/` outside the normal report input tree. The backup directory SHALL be ignored by Git.

#### Scenario: Historical result is redacted
- **WHEN** `gitbench safety-doctor` redacts a file beneath `gitbench-results/`
- **THEN** the original file is copied to the matching relative path beneath `gitbench-results-nsfw/`
- **AND** the backup completes before the source file is replaced

#### Scenario: Existing backup collision
- **WHEN** the intended backup path already exists
- **THEN** the system writes the new original to a collision-safe filename
- **AND** does not overwrite the existing backup

#### Scenario: Clean historical result
- **WHEN** every score in a historical result is allowed
- **THEN** no NSFW backup copy is created

#### Scenario: Newly generated result is redacted
- **WHEN** an in-memory run result contains a redaction before normal serialization
- **THEN** one unsanitized run envelope is written beneath `gitbench-results-nsfw/`
- **AND** normal output destinations receive only the sanitized payload

### Requirement: Atomic fail-closed mutation
The safety doctor SHALL complete classification of every score in an artifact before creating backups or modifying the artifact. Existing-file replacement MUST use an atomic write strategy.

#### Scenario: One score review fails
- **WHEN** any score in an artifact cannot be classified successfully
- **THEN** the safety-doctor operation for that artifact fails
- **AND** the source file remains byte-for-byte unchanged
- **AND** no backup is created for that failed operation

#### Scenario: Successful artifact sweep
- **WHEN** every score in an artifact is classified successfully
- **THEN** required backups are completed
- **AND** the fully sanitized artifact atomically replaces the source file

### Requirement: Historical safety-doctor CLI
The system SHALL provide a `gitbench safety-doctor` command that reviews either an explicit result file or all supported JSON result files in timestamped directories beneath `gitbench-results/`. The command SHALL support a dry-run mode.

#### Scenario: Review explicit result file
- **WHEN** a user runs `gitbench safety-doctor path/to/result.json`
- **THEN** the command reviews and sanitizes that supported result artifact
- **AND** reports reviewed and redacted score counts

#### Scenario: Review timestamped results
- **WHEN** a user runs `gitbench safety-doctor --latest`
- **THEN** the command reviews supported JSON files in every timestamp-named directory beneath `gitbench-results/`

#### Scenario: Dry run
- **WHEN** a user runs `gitbench safety-doctor --dry-run`
- **THEN** the command performs the classifications and prints the planned redactions
- **AND** writes neither backups nor modified result files

#### Scenario: Unsupported JSON shape
- **WHEN** the command receives a JSON artifact shape it cannot traverse safely
- **THEN** it exits with a clear unsupported-format error
- **AND** does not mark the artifact as safety reviewed

### Requirement: New result serialization safety gate
When result safety is configured, the run command SHALL attempt safety review before serializing result content to any normal destination. When review completes, a single sanitized payload SHALL feed JSON files, output directories, JSONL, exports, stdout, and cross-mode aggregation. When review fails because the reviewer cannot complete, the run command SHALL still write doctorable JSON result artifacts with pending safety metadata, SHALL suppress non-doctorable outputs for that payload, and SHALL keep report publication blocked until `gitbench safety-doctor` completes.

#### Scenario: Successful configured run review
- **WHEN** a benchmark run completes and every score is reviewed successfully
- **THEN** all normal serialization destinations receive sanitized content
- **AND** no destination receives an unsanitized representation

#### Scenario: Configured run review fails
- **WHEN** any score in a completed run cannot be reviewed successfully
- **THEN** the run command exits non-zero
- **AND** writes doctorable JSON result artifacts for completed benchmark work
- **AND** marks those JSON artifacts with pending result-safety metadata
- **AND** suppresses JSONL, export, and stdout JSON serialization for that payload

#### Scenario: Redaction does not change score
- **WHEN** a newly generated score is classified for redaction
- **THEN** its generated content is sanitized before serialization
- **AND** its benchmark evaluation values remain those produced before the safety pass

### Requirement: Report publication validation
When result safety is configured, report generation SHALL reject every input artifact that lacks complete current-policy safety metadata or whose reviewed content hashes no longer match. Report generation MUST NOT invoke the reviewer implicitly.

#### Scenario: Fully reviewed report inputs
- **WHEN** every report input has complete current-policy metadata and matching hashes
- **THEN** `gitbench report` aggregates and publishes the sanitized data

#### Scenario: Unswept historical input
- **WHEN** any report input lacks safety metadata
- **THEN** `gitbench report` exits with an error naming the input artifact
- **AND** directs the user to run `gitbench safety-doctor`

#### Scenario: Stale or modified reviewed input
- **WHEN** an input uses an older policy version or its current content hash does not match recorded metadata
- **THEN** report generation rejects that input as requiring another safety sweep

#### Scenario: No hidden reviewer call
- **WHEN** report validation encounters an unsafe-to-publish artifact
- **THEN** the report command performs no model request
- **AND** produces no updated report artifacts
