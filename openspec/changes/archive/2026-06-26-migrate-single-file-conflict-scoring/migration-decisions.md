# Single-File Conflict Scoring Migration Decisions

## Scope

Reviewed single-file conflict fixtures in:

- `fixtures/merge_conflicts`
- `fixtures/cherry_pick`
- `fixtures/rebase`

Existing multi-file fixtures `f010` and `f012` in each benchmark already use
`resolved_file_blocks` and are not migration candidates for this follow-up.

## Replay Path

Local stored-attempt replay is provided by:

```bash
python tools/replay_single_file_conflict_scoring.py \
  --json-out openspec/changes/migrate-single-file-conflict-scoring/replay-single-file-conflict-scoring.json \
  --markdown-out openspec/changes/migrate-single-file-conflict-scoring/replay-single-file-conflict-scoring.md
```

The replay compares current `exact_match` scoring against candidate
`resolved_file_blocks` scoring with one `expected_files` entry. For a single
expected file, the scorer treats unheaded whole-answer content as that file's
content and still accepts explicit filename headings.

## Replay Summary

- Candidate fixtures: 30
- Stored attempts replayed: 3,840
- Before passes: 2,782
- After passes: 2,816
- Newly passing outputs: 35
- Newly failing outputs: 1
- Expected-answer checks: all candidates pass before migration, as raw
  single-file content after migration, and as explicit file blocks after
  migration.

## Candidate Inventory

All candidates name exactly one filename in the prompt and ask for the resolved
content for that file. No single-file conflict fixture needs to remain on
`exact_match` without replay due to a missing file/content contract.

| Fixture | File | Current prompt shape | Current scorer | Decision |
| --- | --- | --- | --- | --- |
| `merge_conflicts/f001` | `greeting.txt` | raw resolved content | `exact_match`, `strip_fences` | migrate |
| `merge_conflicts/f002` | `version.txt` | raw resolved content | `exact_match`, `strip_fences` | migrate |
| `merge_conflicts/f003` | `status.txt` | raw resolved content | `exact_match`, `strip_fences` | migrate |
| `merge_conflicts/f004` | `contact.txt` | raw resolved content | `exact_match`, `strip_fences`, ordered | migrate |
| `merge_conflicts/f005` | `greet.py` | raw resolved content | `exact_match`, `strip_fences`, ordered | migrate |
| `merge_conflicts/f006` | `config.yaml` | raw resolved content | `exact_match`, `strip_fences`, ordered | migrate |
| `merge_conflicts/f007` | `config.txt` | raw resolved content | `exact_match`, `strip_fences`, ordered | migrate |
| `merge_conflicts/f008` | `project.txt` | raw resolved content | `exact_match`, `strip_fences` | migrate |
| `merge_conflicts/f009` | `author.txt` | raw resolved content | `exact_match` | migrate |
| `merge_conflicts/f011` | `settings.json` | raw resolved content | `exact_match`, `strip_fences`, ordered | migrate |
| `cherry_pick/f001` | `greeting.txt` | raw resolved content | `exact_match`, `strip_fences` | migrate |
| `cherry_pick/f002` | `version.txt` | raw resolved content | `exact_match`, `strip_fences` | migrate |
| `cherry_pick/f003` | `status.txt` | raw resolved content | `exact_match`, `strip_fences` | migrate |
| `cherry_pick/f004` | `contact.txt` | raw resolved content | `exact_match`, `strip_fences`, ordered | migrate |
| `cherry_pick/f005` | `greet.py` | raw resolved content | `exact_match`, `strip_fences`, ordered | migrate |
| `cherry_pick/f006` | `config.yaml` | raw resolved content | `exact_match`, `strip_fences`, ordered | migrate |
| `cherry_pick/f007` | `config.txt` | raw resolved content | `exact_match`, `strip_fences`, ordered | migrate |
| `cherry_pick/f008` | `project.txt` | raw resolved content | `exact_match`, `strip_fences` | migrate |
| `cherry_pick/f009` | `author.txt` | raw resolved content | `exact_match` | migrate |
| `cherry_pick/f011` | `settings.json` | raw resolved content | `exact_match`, `strip_fences`, ordered | migrate |
| `rebase/f001` | `greeting.txt` | raw resolved content | `exact_match`, `strip_fences` | migrate |
| `rebase/f002` | `version.txt` | raw resolved content | `exact_match` | migrate |
| `rebase/f003` | `status.txt` | raw resolved content | `exact_match` | migrate |
| `rebase/f004` | `contact.txt` | raw resolved content | `exact_match`, `strip_fences`, ordered | migrate |
| `rebase/f005` | `greet.py` | raw resolved content | `exact_match`, `strip_fences`, ordered | migrate |
| `rebase/f006` | `config.yaml` | raw resolved content | `exact_match`, `strip_fences`, ordered | migrate |
| `rebase/f007` | `config.txt` | raw resolved content | `exact_match`, `strip_fences`, ordered | migrate |
| `rebase/f008` | `project.txt` | raw resolved content | `exact_match`, `strip_fences` | migrate |
| `rebase/f009` | `author.txt` | raw resolved content | `exact_match` | migrate |
| `rebase/f011` | `settings.json` | raw resolved content | `exact_match`, `strip_fences`, ordered | migrate |

## Manual Review

Newly passing outputs were inspected from the replay report and JSON. They are
semantically correct answers that previously failed only because they included a
filename heading, a wrapping code fence, or trailing spaces around otherwise
correct resolved content.

The single newly failing stored output was `rebase/f008` with:

```text
 Title: My Project v3
```

This is an intentional stricter failure under file-content scoring: the leading
space changes the resolved file content rather than merely wrapping the answer.

## Final Decisions

- Migrate all 30 single-file candidates to `resolved_file_blocks`.
- Keep their current raw `expected` values so the existing single-file text and
  JSON-schema prompt shape remains comparable.
- Add `scoring.expected_files` with the prompt filename mapped to the expected
  resolved content.
- Do not add `output_schema: resolved_file_blocks` to these single-file fixtures;
  the benchmark default `resolved_content` schema remains appropriate for
  single-file JSON-schema runs.
- Leave `f010` and `f012` in each benchmark unchanged because they are already
  multi-file `resolved_file_blocks` fixtures.
- A full campaign rerun is not required for this follow-up; local replay of
  stored attempts plus expected-answer checks cover the migration decision.
