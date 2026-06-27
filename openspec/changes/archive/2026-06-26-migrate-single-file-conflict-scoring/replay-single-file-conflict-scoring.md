# Single-File Conflict Scoring Replay

Candidate scorer: `resolved_file_blocks` with one `expected_files` entry. Single-file unheaded content is treated as that file's content; named file blocks are also accepted.

## Summary

- Candidate fixtures: 30
- Stored attempts replayed: 3840
- Before passes: 2782
- After passes: 2816
- Newly passing outputs: 35
- Newly failing outputs: 1

## Fixture Results

| Fixture | File | Expected checks | Attempts | Before | After | Delta | Decision evidence |
| --- | --- | --- | ---: | ---: | ---: | ---: | --- |
| `cherry_pick/f001` | `greeting.txt` | pass/pass/pass | 128 | 90 | 90 | +0 | 0 newly passing; 0 newly failing |
| `cherry_pick/f002` | `version.txt` | pass/pass/pass | 128 | 108 | 110 | +2 | 2 newly passing; 0 newly failing |
| `cherry_pick/f003` | `status.txt` | pass/pass/pass | 128 | 114 | 116 | +2 | 2 newly passing; 0 newly failing |
| `cherry_pick/f004` | `contact.txt` | pass/pass/pass | 128 | 20 | 22 | +2 | 2 newly passing; 0 newly failing |
| `cherry_pick/f005` | `greet.py` | pass/pass/pass | 128 | 9 | 9 | +0 | 0 newly passing; 0 newly failing |
| `cherry_pick/f006` | `config.yaml` | pass/pass/pass | 128 | 95 | 102 | +7 | 7 newly passing; 0 newly failing |
| `cherry_pick/f007` | `config.txt` | pass/pass/pass | 128 | 116 | 116 | +0 | 0 newly passing; 0 newly failing |
| `cherry_pick/f008` | `project.txt` | pass/pass/pass | 128 | 115 | 115 | +0 | 0 newly passing; 0 newly failing |
| `cherry_pick/f009` | `author.txt` | pass/pass/pass | 128 | 116 | 118 | +2 | 2 newly passing; 0 newly failing |
| `cherry_pick/f011` | `settings.json` | pass/pass/pass | 128 | 102 | 102 | +0 | 0 newly passing; 0 newly failing |
| `merge_conflicts/f001` | `greeting.txt` | pass/pass/pass | 128 | 85 | 85 | +0 | 0 newly passing; 0 newly failing |
| `merge_conflicts/f002` | `version.txt` | pass/pass/pass | 128 | 114 | 114 | +0 | 0 newly passing; 0 newly failing |
| `merge_conflicts/f003` | `status.txt` | pass/pass/pass | 128 | 104 | 104 | +0 | 0 newly passing; 0 newly failing |
| `merge_conflicts/f004` | `contact.txt` | pass/pass/pass | 128 | 89 | 90 | +1 | 1 newly passing; 0 newly failing |
| `merge_conflicts/f005` | `greet.py` | pass/pass/pass | 128 | 25 | 25 | +0 | 0 newly passing; 0 newly failing |
| `merge_conflicts/f006` | `config.yaml` | pass/pass/pass | 128 | 97 | 97 | +0 | 0 newly passing; 0 newly failing |
| `merge_conflicts/f007` | `config.txt` | pass/pass/pass | 128 | 112 | 112 | +0 | 0 newly passing; 0 newly failing |
| `merge_conflicts/f008` | `project.txt` | pass/pass/pass | 128 | 117 | 117 | +0 | 0 newly passing; 0 newly failing |
| `merge_conflicts/f009` | `author.txt` | pass/pass/pass | 128 | 116 | 116 | +0 | 0 newly passing; 0 newly failing |
| `merge_conflicts/f011` | `settings.json` | pass/pass/pass | 128 | 101 | 101 | +0 | 0 newly passing; 0 newly failing |
| `rebase/f001` | `greeting.txt` | pass/pass/pass | 128 | 85 | 85 | +0 | 0 newly passing; 0 newly failing |
| `rebase/f002` | `version.txt` | pass/pass/pass | 128 | 114 | 116 | +2 | 2 newly passing; 0 newly failing |
| `rebase/f003` | `status.txt` | pass/pass/pass | 128 | 117 | 117 | +0 | 0 newly passing; 0 newly failing |
| `rebase/f004` | `contact.txt` | pass/pass/pass | 128 | 74 | 75 | +1 | 1 newly passing; 0 newly failing |
| `rebase/f005` | `greet.py` | pass/pass/pass | 128 | 4 | 4 | +0 | 0 newly passing; 0 newly failing |
| `rebase/f006` | `config.yaml` | pass/pass/pass | 128 | 95 | 105 | +10 | 10 newly passing; 0 newly failing |
| `rebase/f007` | `config.txt` | pass/pass/pass | 128 | 116 | 116 | +0 | 0 newly passing; 0 newly failing |
| `rebase/f008` | `project.txt` | pass/pass/pass | 128 | 114 | 115 | +1 | 2 newly passing; 1 newly failing |
| `rebase/f009` | `author.txt` | pass/pass/pass | 128 | 117 | 121 | +4 | 4 newly passing; 0 newly failing |
| `rebase/f011` | `settings.json` | pass/pass/pass | 128 | 101 | 101 | +0 | 0 newly passing; 0 newly failing |

## Changed Outputs

### `cherry_pick/f001`

### `cherry_pick/f002`

- newly passing: `liquid/lfm-2-24b-a2b` `text` from `gitbench-results-bak/20260616T192400Z/2026-06-17T02-02-15_liquid_lfm-2-24b-a2b_text_v0.3.0.json`

  ```text
  version.txt
  VERSION=2.0.0
  ```

- newly passing: `liquid/lfm-2-24b-a2b` `json_schema` from `gitbench-results-bak/20260616T192400Z/2026-06-17T10-04-30_liquid_lfm-2-24b-a2b_json_schema_v0.3.0.json`

  ```text
  version.txt
  VERSION=2.0.0
  ```

### `cherry_pick/f003`

- newly passing: `liquid/lfm-2-24b-a2b` `text` from `gitbench-results-bak/20260616T192400Z/2026-06-17T02-02-15_liquid_lfm-2-24b-a2b_text_v0.3.0.json`

  ```text
  status.txt
  Status: Resolved
  ```

- newly passing: `liquid/lfm-2-24b-a2b` `json_schema` from `gitbench-results-bak/20260616T192400Z/2026-06-17T10-04-30_liquid_lfm-2-24b-a2b_json_schema_v0.3.0.json`

  ```text
  status.txt
  Status: Resolved
  ```

### `cherry_pick/f004`

- newly passing: `nvidia/nemotron-3-super-120b-a12b:none` `text` from `gitbench-results-bak/20260616T192400Z/2026-06-17T02-02-15_nvidia_nemotron-3-super-120b-a12b-none_text_v0.3.0.json`

  ```text
  --- contact.txt
  Name: John Doe
  Email: johndoe@personal.com
  Phone: 555-9876
  ```

- newly passing: `ibm-granite/granite-4.1-8b` `json_schema` from `gitbench-results-bak/20260616T192400Z/2026-06-17T10-04-30_ibm-granite_granite-4.1-8b_json_schema_v0.3.0.json`

  ```text
  --- contact.txt
  Name: John Doe
  Email: johndoe@personal.com
  Phone: 555-9876
  ```

### `cherry_pick/f005`

### `cherry_pick/f006`

- newly passing: `nvidia/nemotron-3-nano-30b-a3b:high` `text` from `gitbench-results-bak/20260616T192400Z/2026-06-17T02-02-15_nvidia_nemotron-3-nano-30b-a3b-high_text_v0.3.0.json`

  ```text
  --- config.yaml
  server:
    port: 443
    host: 0.0.0.0
  ```

- newly passing: `nvidia/nemotron-3-nano-30b-a3b:xhigh` `text` from `gitbench-results-bak/20260616T192400Z/2026-06-17T02-02-15_nvidia_nemotron-3-nano-30b-a3b-xhigh_text_v0.3.0.json`

  ```text
  --- config.yaml
  server:
    port: 443
    host: 0.0.0.0
  ```

- newly passing: `nvidia/nemotron-3-nano-30b-a3b:medium` `json_schema` from `gitbench-results-bak/20260616T192400Z/2026-06-17T10-04-30_nvidia_nemotron-3-nano-30b-a3b-medium_json_schema_v0.3.0.json`

  ```text
  --- config.yaml
  server:
    port: 443
    host: 0.0.0.0
  ```

- newly passing: `anthropic/claude-sonnet-4.6:high` `json_schema` from `gitbench-results-bak/20260617T202311Z/2026-06-18T08-34-06_anthropic_claude-sonnet-4.6-high_json_schema_v0.3.0.json`

  ```text
  --- config.yaml
  server:
    port: 443
    host: 0.0.0.0
  ```

- newly passing: `anthropic/claude-sonnet-4.6:medium` `json_schema` from `gitbench-results-bak/20260617T202311Z/2026-06-18T08-34-06_anthropic_claude-sonnet-4.6-medium_json_schema_v0.3.0.json`

  ```text
  --- config.yaml
  server:
    port: 443
    host: 0.0.0.0
  ```

- 2 additional changed outputs omitted.

### `cherry_pick/f007`

### `cherry_pick/f008`

### `cherry_pick/f009`

- newly passing: `liquid/lfm-2-24b-a2b` `text` from `gitbench-results-bak/20260616T192400Z/2026-06-17T02-02-15_liquid_lfm-2-24b-a2b_text_v0.3.0.json`

  ```text
  ```txt
  Author: J. Doe
  ```
  ```

- newly passing: `liquid/lfm-2-24b-a2b` `json_schema` from `gitbench-results-bak/20260616T192400Z/2026-06-17T10-04-30_liquid_lfm-2-24b-a2b_json_schema_v0.3.0.json`

  ```text
  ```txt
  Author: J. Doe
  ```
  ```

### `cherry_pick/f011`

### `merge_conflicts/f001`

### `merge_conflicts/f002`

### `merge_conflicts/f003`

### `merge_conflicts/f004`

- newly passing: `ibm-granite/granite-4.1-8b` `text` from `gitbench-results-bak/20260616T192400Z/2026-06-17T02-02-15_ibm-granite_granite-4.1-8b_text_v0.3.0.json`

  ```text
  Name: John Doe  
  Email: johndoe@personal.com  
  Phone: 555-9876
  ```

### `merge_conflicts/f005`

### `merge_conflicts/f006`

### `merge_conflicts/f007`

### `merge_conflicts/f008`

### `merge_conflicts/f009`

### `merge_conflicts/f011`

### `rebase/f001`

### `rebase/f002`

- newly passing: `anthropic/claude-opus-4.8:max` `text` from `gitbench-results/20260625T212156Z/2026-06-25T22-15-08_anthropic_claude-opus-4.8-max_text_v0.3.1.json`

  ```text
  ```
  VERSION=1.1.0
  ```
  ```

- newly passing: `liquid/lfm-2-24b-a2b` `json_schema` from `gitbench-results-bak/20260616T192400Z/2026-06-17T10-04-30_liquid_lfm-2-24b-a2b_json_schema_v0.3.0.json`

  ```text
  version.txt
  VERSION=1.1.0
  ```

### `rebase/f003`

### `rebase/f004`

- newly passing: `ibm-granite/granite-4.1-8b` `json_schema` from `gitbench-results-bak/20260616T192400Z/2026-06-17T10-04-30_ibm-granite_granite-4.1-8b_json_schema_v0.3.0.json`

  ```text
  --- contact.txt
  Name: John Doe
  Email: johndoe@personal.com
  Phone: 555-9876
  ```

### `rebase/f005`

### `rebase/f006`

- newly passing: `poolside/laguna-xs.2:high` `json_schema` from `gitbench-results/20260622T213630Z/2026-06-23T01-05-04_poolside_laguna-xs.2-high_json_schema_v0.3.1.json`

  ```text
  --- config.yaml
  server:
    port: 443
    host: 0.0.0.0
  ```

- newly passing: `poolside/laguna-xs.2:none` `json_schema` from `gitbench-results/20260622T213630Z/2026-06-23T01-05-04_poolside_laguna-xs.2-none_json_schema_v0.3.1.json`

  ```text
  --- config.yaml
  server:
    port: 443
    host: 0.0.0.0
  ```

- newly passing: `nvidia/nemotron-3-nano-30b-a3b:medium` `text` from `gitbench-results-bak/20260616T192400Z/2026-06-17T02-02-15_nvidia_nemotron-3-nano-30b-a3b-medium_text_v0.3.0.json`

  ```text
  --- config.yaml
  server:
    port: 443
    host: 0.0.0.0
  ```

- newly passing: `nvidia/nemotron-3-super-120b-a12b:low` `text` from `gitbench-results-bak/20260616T192400Z/2026-06-17T02-02-15_nvidia_nemotron-3-super-120b-a12b-low_text_v0.3.0.json`

  ```text
  --- config.yaml
  server:
    port: 443
    host: 0.0.0.0
  ```

- newly passing: `nvidia/nemotron-3-nano-30b-a3b:medium` `json_schema` from `gitbench-results-bak/20260616T192400Z/2026-06-17T10-04-30_nvidia_nemotron-3-nano-30b-a3b-medium_json_schema_v0.3.0.json`

  ```text
  --- config.yaml
  server:
    port: 443
    host: 0.0.0.0
  ```

- 5 additional changed outputs omitted.

### `rebase/f007`

### `rebase/f008`

- newly passing: `liquid/lfm-2-24b-a2b` `text` from `gitbench-results-bak/20260616T192400Z/2026-06-17T02-02-15_liquid_lfm-2-24b-a2b_text_v0.3.0.json`

  ```text
  project.txt
  Title: My Project v3
  ```

- newly passing: `liquid/lfm-2-24b-a2b` `json_schema` from `gitbench-results-bak/20260616T192400Z/2026-06-17T10-04-30_liquid_lfm-2-24b-a2b_json_schema_v0.3.0.json`

  ```text
  project.txt
  Title: My Project v3
  ```

- newly failing: `deepseek/deepseek-v4-flash:high` `json_schema` from `gitbench-results/20260622T213630Z/2026-06-23T01-05-04_deepseek_deepseek-v4-flash-high_json_schema_v0.3.1.json`

  ```text
   Title: My Project v3
  ```

### `rebase/f009`

- newly passing: `anthropic/claude-opus-4.8:max` `text` from `gitbench-results/20260625T212156Z/2026-06-25T22-15-08_anthropic_claude-opus-4.8-max_text_v0.3.1.json`

  ```text
  ```
  Author: J. Doe
  ```
  ```

- newly passing: `liquid/lfm-2-24b-a2b` `text` from `gitbench-results-bak/20260616T192400Z/2026-06-17T02-02-15_liquid_lfm-2-24b-a2b_text_v0.3.0.json`

  ```text
  author.txt
  Author: J. Doe
  ```

- newly passing: `liquid/lfm-2-24b-a2b` `json_schema` from `gitbench-results-bak/20260616T192400Z/2026-06-17T10-04-30_liquid_lfm-2-24b-a2b_json_schema_v0.3.0.json`

  ```text
  author.txt
  Author: J. Doe
  ```

- newly passing: `anthropic/claude-opus-4.8:high` `text` from `gitbench-results-bak/20260617T202311Z/2026-06-18T01-45-40_anthropic_claude-opus-4.8-high_text_v0.3.0.json`

  ```text
  ```
  Author: J. Doe
  ```
  ```

### `rebase/f011`
