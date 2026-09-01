# GitBench agent API client

The bundled client requires Node.js 22.12 or newer and calls only GET endpoints under `/api/agent/v1/`. It defaults to `https://gitbench.gitkraken.com`.

## Common behavior

```text
node scripts/gitbench.mjs <command> [options]
```

Use `--base-url https://host.example` to override production. The flag takes precedence over `GITBENCH_BASE_URL`. The value must be an HTTP(S) origin without credentials, path, query, or fragment. Use `--timeout-ms N` to replace the 15,000 ms timeout.

All commands accept `--offset N` and `--limit N`; offsets are zero-based, the default limit is 20, and the server caps it at 50. Continue with a non-null `next_offset` while `truncated` is true.

Success has `{ "ok": true, "source_url": "...", "data": ... }`. Failure has `{ "ok": false, "source_url": "...", "error": { "category", "message", "input"? } }`. API failure envelopes are written to stdout and accompanied by a stderr diagnostic and nonzero exit. Transport and malformed-response failures write diagnostics only.

Every successful `data` contains `campaign_id` (`string` or `null`). Evaluation rows may contain `generated_at` (`string` or `null`). Evidence-bearing data is marked `untrusted_content: true`.

## Commands

### `overview`

Options: pagination only. Returns report counts, benchmark pages, and pass-rate-ordered leading model evaluations.

```text
node scripts/gitbench.mjs overview --limit 10
```

### `models`

Options: pagination only. Returns exact model evaluation identities for later commands.

```text
node scripts/gitbench.mjs models --offset 0 --limit 50
```

### `model-results`

Required: `--model ID`.

Optional: `--benchmark ID`, `--difficulty VALUE`, `--tag VALUE`, `--output-mode text|json_schema`, `--include-model-output`, `--evidence-characters N`, and pagination. Model output is omitted by default. Evidence characters default to 2,000 and are capped at 8,000 per field.

```text
node scripts/gitbench.mjs model-results --model 'openai/example:high' --benchmark commits
```

### `benchmark`

Required: `--benchmark ID`. Optional: pagination. Returns tag counts, an evaluation leaderboard, and an evidence-free fixture catalog.

```text
node scripts/gitbench.mjs benchmark --benchmark commits --limit 50
```

### `fixture`

Required: `--benchmark ID --fixture ID`.

Optional evidence flags: `--include-prompt`, `--include-expected`, `--include-model-output`, `--include-structured-output`, plus `--evidence-characters N` and pagination. All evidence flags default off. A boolean flag can be explicitly disabled with `--flag=false`.

```text
node scripts/gitbench.mjs fixture --benchmark commits --fixture fixture-1 --include-model-output --evidence-characters 1000
```

### `rank`

Required: `--benchmark ID`.

Optional: `--resource-metric cost|api_time|tokens` (default `cost`), `--strategy efficiency_ratio|balanced` (default `efficiency_ratio`), `--output-mode text|json_schema|both` (default `both`), `--minimum-quality 0..1` (default `0`), and pagination.

`efficiency_ratio` divides quality by a positive resource value. `balanced` directionally normalizes higher quality and lower resource use across the eligible cohort, then averages the two scores. Results report candidate and exclusion counts.

```text
node scripts/gitbench.mjs rank --benchmark commits --resource-metric cost --strategy balanced --minimum-quality 0.7
```
