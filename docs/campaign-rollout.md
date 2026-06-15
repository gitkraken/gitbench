# Evaluation Campaign Rollout Guide

This document describes how to roll out repeated evaluation campaigns, estimate the
additional cost and storage they create, repair or resume a campaign, and roll back to
a one-trial campaign if needed.

## Default behavior

GitBench now runs every selected model, reasoning effort, output mode, and fixture
combination for a configurable number of complete **trial rounds**. The default number
of trials is **three**.

- The CLI flag `--trials N` overrides the default for a single run.
- The configuration key `campaign.default_trials` overrides the default globally.
- A value of `1` produces a one-trial campaign, equivalent to the legacy single-run
  behavior but still stored in the campaign-aware schema.
- Published evaluations may choose a higher number such as five; the UI and schema
  semantics do not depend on a particular count.

## Call multiplication

A campaign multiplies the number of target-model calls:

```
target calls = trials × fixtures × models × reasoning_efforts × output_modes
```

For example, with 204 fixtures, 10 models, 2 reasoning efforts, 2 output modes, and
3 trials:

```
204 × 10 × 2 × 2 × 3 = 24,480 target calls
```

If LLM-judge scoring is enabled, each valid target attempt typically requires one
additional judge call. Safety review, when configured, is evaluated once per retained
raw attempt. The CLI campaign plan prints the estimated target, judge, and safety-review
call counts before execution begins.

## Storage growth

One immutable raw-attempt envelope is written per execution unit under
`gitbench-results/<campaign-id>/envelopes/`. The manifest `campaign.json` is updated
atomically. Storage growth is roughly proportional to the number of attempts:

```
envelopes = target calls + any retried/repaired attempts
```

Aggregate report generation consumes the raw envelopes and does not replace them, so
the raw evidence remains available for drilldowns.

## Repair procedure

1. Identify the campaign ID from the CLI output or the `gitbench-results/` directory.
2. Load the campaign manifest to see which attempts are missing, invalidated by hash
   mismatch, or marked as infrastructure failures.
3. Use the normal run command with `--campaign-id <id>` to resume; completed valid
   attempts are reused and only missing or explicitly repairable identities are
   scheduled.
4. To target a single failed attempt, use the repair workflow scoped to the exact
   campaign attempt identity. Prior retry and failure history is preserved in the
   envelope.

## Rollback to one-trial campaigns

To disable repeated scheduling while keeping the new schema:

1. Set `campaign.default_trials` to `1` or pass `--trials 1`.
2. New campaigns will contain a single trial round.
3. Existing multi-trial campaigns remain readable; only new campaigns are affected.

The legacy single-result artifact format is still supported through the compatibility
importer, which converts historical results into one-trial legacy campaigns.
