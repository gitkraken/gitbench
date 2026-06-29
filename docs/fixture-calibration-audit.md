# Fixture Calibration Audit

Run this report from the repository root:

```bash
.venv/bin/python -m gitbench.fixture_audit --threshold 0.5 --representative-failures 3
```

The report ranks fixtures by pass rate from `web/data/gitbench.db`, joins
fixture YAML metadata for scoring type and difficulty, and includes representative
failed outputs.

Audit threshold: fixtures at or below 50% observed pass rate in the current report
database.

## Zero-Pass Fixtures

| Fixture | Primary classification | Action |
| --- | --- | --- |
| `git_log_format/f002` | Scoring brittleness | Use `unordered_line_set` because order is not required by the prompt. |
| `git_log_format/f003` | Scoring brittleness | Use `unordered_line_set` because order is not required by the prompt. |
| `git_log_format/f007` | Expected-value defect | Use `commit_hash_by_subject` with `hash_length: short`. |
| `git_log_format/f010` | Setup defect | Force non-fast-forward merges and validate the derived merge count. |

## Low-Pass Classifications

| Fixture or cluster | Primary classification | Notes |
| --- | --- | --- |
| `git_grep/f003` | Setup defect | Fixture overwrote `src/api.py`; setup now appends lines and derives count. |
| `git_grep/f005`, `git_grep/f007`, `git_grep/f011` | Expected-value defect | Counts included `.grep_command`; benchmark output now filters the sentinel and expected values match visible output. |
| `git_grep/f004`, `git_grep/f012` | Prompt/scoring brittleness | Normalize output contract for comma formatting and filename-only count interpretation. |
| `rebase/f002`, `rebase/f003`, `rebase/f009` | Prompt ambiguity | Prompts had rebase polarity ambiguity; they now declare the current branch policy explicitly. |
| `cherry_pick/f009`, `merge_conflicts/f009` | Prompt ambiguity | Prompts now state the current/second-side resolution policy explicitly. |
| `blame_forensics/f005`, `blame_forensics/f006`, `blame_forensics/f010` | Prompt/context mismatch | Prompts asked for blame analysis but benchmark context only showed log output; blame context is now included. |
| `commit_squash/f001`, `commit_squash/f002`, `commit_squash/f004` | Output-contract ambiguity | Prompts now require selected commits only; scorer continues rejecting extra selected commits. |
| Other low-pass fixtures under 50% | Genuine difficulty or pending manual review | Left unchanged unless a concrete setup, expected-value, or prompt defect was identified. |

## Difficulty Recalibration

Historical pass-rate bands were used to prioritize the audit, but fixture defects
were corrected before changing difficulty labels. Because the stored result database
contains `0.1.0` runs with known-broken scoring/setup behavior, those pass rates are
not used directly to harden labels. The `0.2.0` suite version separates future
post-fix observations.

Manual review after the corrections keeps the current labels for the audited
fixtures:

| Fixtures | Label | Manual review |
| --- | --- | --- |
| `git_log_format/f002`, `git_log_format/f003`, `git_log_format/f007` | `easy` | Straightforward log filtering or short-hash lookup after deterministic scoring fixes. |
| `git_log_format/f010` | `medium` | Requires understanding merge commits and `git log --merges`; setup now creates real merge commits. |
| `git_grep/f004`, `git_grep/f005` | `easy` | Simple formatting/count interpretation after sentinel filtering and expected-value correction. |
| `git_grep/f003`, `git_grep/f007`, `git_grep/f011`, `git_grep/f012` | `medium` | Regex, context, multi-pattern, and count-mode interpretation remain moderately complex. |
| `rebase/f002`, `rebase/f003` | `easy` | Single-file conflict resolution with explicit current-branch policy. |
| `rebase/f009`, `cherry_pick/f009`, `merge_conflicts/f009` | `medium` | Three-way conflict reasoning remains the tested skill after policy clarification. |
| `blame_forensics/f005`, `blame_forensics/f006`, `blame_forensics/f010` | `medium` | Requires tracing bug-introducing commits with log and blame context. |
| `commit_squash/f001`, `commit_squash/f002` | `easy` | Obvious WIP/fixup selection once output instructions are constrained. |
| `commit_squash/f004` | `medium` | Requires selecting intermediate WIP commits without including the completed feature commit. |

After enough `0.2.0` runs are stored, run the audit report again and use these bands
as review input:

| Post-fix pass rate | Suggested label |
| ---: | --- |
| `>= 80%` | `easy` unless the fixture uses multi-step or hazardous Git reasoning. |
| `50%` to `< 80%` | `medium` unless manual review shows a narrow formatting task. |
| `20%` to `< 50%` | `hard` when failures are not explained by setup, prompt, or scoring defects. |
| `< 20%` | `expert` only after re-auditing for fixture defects and ambiguity. |
