PRAGMA foreign_keys = ON;

CREATE TABLE models (
  name TEXT NOT NULL,
  provider TEXT NOT NULL,
  base_model TEXT NOT NULL,
  reasoning_level TEXT,
  output_mode TEXT NOT NULL DEFAULT 'text',
  PRIMARY KEY (name, output_mode)
);

CREATE TABLE benchmarks (
  name TEXT PRIMARY KEY
);

CREATE TABLE runs (
  id INTEGER PRIMARY KEY,
  timestamp TEXT NOT NULL,
  model_name TEXT NOT NULL,
  output_mode TEXT NOT NULL DEFAULT 'text',
  profile TEXT NOT NULL,
  git_sha TEXT NOT NULL,
  benchmark_suite_version TEXT NOT NULL,
  reasoning_level TEXT NOT NULL,
  FOREIGN KEY (model_name, output_mode) REFERENCES models(name, output_mode) ON DELETE CASCADE
);

CREATE TABLE model_summaries (
  model_name TEXT NOT NULL,
  output_mode TEXT NOT NULL DEFAULT 'text',
  total_runs INTEGER NOT NULL,
  total_fixtures INTEGER NOT NULL,
  total_passed INTEGER NOT NULL,
  pass_at_k REAL NOT NULL,
  total_cost_usd REAL,
  avg_cost_usd REAL,
  PRIMARY KEY (model_name, output_mode),
  FOREIGN KEY (model_name, output_mode) REFERENCES models(name, output_mode) ON DELETE CASCADE
);

CREATE TABLE model_runtimes (
  model_name TEXT NOT NULL,
  output_mode TEXT NOT NULL DEFAULT 'text',
  total_ms REAL NOT NULL,
  avg_ms REAL NOT NULL,
  min_ms REAL NOT NULL,
  max_ms REAL NOT NULL,
  fixture_count INTEGER NOT NULL,
  PRIMARY KEY (model_name, output_mode),
  FOREIGN KEY (model_name, output_mode) REFERENCES models(name, output_mode) ON DELETE CASCADE
);

CREATE TABLE benchmark_summaries (
  model_name TEXT NOT NULL,
  output_mode TEXT NOT NULL DEFAULT 'text',
  benchmark_name TEXT NOT NULL REFERENCES benchmarks(name) ON DELETE CASCADE,
  pass_at_k REAL NOT NULL,
  total INTEGER NOT NULL,
  passed INTEGER NOT NULL,
  avg_similarity REAL NOT NULL,
  PRIMARY KEY (model_name, output_mode, benchmark_name),
  FOREIGN KEY (model_name, output_mode) REFERENCES models(name, output_mode) ON DELETE CASCADE
);

CREATE TABLE fixtures (
  benchmark_name TEXT NOT NULL REFERENCES benchmarks(name) ON DELETE CASCADE,
  fixture_id TEXT NOT NULL,
  prompt TEXT NOT NULL,
  expected TEXT NOT NULL,
  description TEXT NOT NULL,
  setup_json TEXT NOT NULL,
  purpose TEXT NOT NULL,
  difficulty TEXT NOT NULL,
  PRIMARY KEY (benchmark_name, fixture_id)
);

CREATE TABLE fixture_tags (
  benchmark_name TEXT NOT NULL,
  fixture_id TEXT NOT NULL,
  tag TEXT NOT NULL,
  PRIMARY KEY (benchmark_name, fixture_id, tag),
  FOREIGN KEY (benchmark_name, fixture_id)
    REFERENCES fixtures(benchmark_name, fixture_id) ON DELETE CASCADE
);

CREATE TABLE fixture_results (
  id INTEGER PRIMARY KEY,
  model_name TEXT NOT NULL,
  output_mode TEXT NOT NULL DEFAULT 'text',
  benchmark_name TEXT NOT NULL,
  fixture_id TEXT NOT NULL,
  passed INTEGER NOT NULL,
  similarity REAL NOT NULL,
  error TEXT,
  model_output TEXT NOT NULL,
  reasoning_level TEXT,
  input_tokens INTEGER,
  output_tokens INTEGER,
  total_tokens INTEGER,
  cost_usd REAL,
  duration_ms REAL,
  api_duration_ms REAL,
  purpose TEXT,
  difficulty TEXT,
  tags_json TEXT NOT NULL,
  parsed_payload TEXT,
  raw_structured_output TEXT,
  structured_error TEXT,
  FOREIGN KEY (benchmark_name, fixture_id)
    REFERENCES fixtures(benchmark_name, fixture_id) ON DELETE CASCADE
);

CREATE TABLE base_model_groups (
  id INTEGER PRIMARY KEY,
  provider TEXT NOT NULL,
  base_model TEXT NOT NULL,
  UNIQUE (provider, base_model)
);

CREATE TABLE base_model_group_levels (
  group_id INTEGER NOT NULL REFERENCES base_model_groups(id) ON DELETE CASCADE,
  level TEXT,
  model_name TEXT NOT NULL,
  output_mode TEXT NOT NULL DEFAULT 'text',
  pass_at_k REAL NOT NULL,
  total_cost_usd REAL,
  PRIMARY KEY (group_id, model_name, output_mode),
  FOREIGN KEY (model_name, output_mode) REFERENCES models(name, output_mode) ON DELETE CASCADE
);

CREATE INDEX idx_fixture_results_model_benchmark
  ON fixture_results(model_name, output_mode, benchmark_name);
CREATE INDEX idx_fixture_results_model_difficulty
  ON fixture_results(model_name, output_mode, difficulty, benchmark_name, fixture_id);
CREATE INDEX idx_fixture_results_benchmark_fixture
  ON fixture_results(benchmark_name, fixture_id);
CREATE INDEX idx_fixture_results_benchmark_model_fixture
  ON fixture_results(benchmark_name, model_name, output_mode, fixture_id);
CREATE INDEX idx_fixtures_benchmark
  ON fixtures(benchmark_name);
CREATE INDEX idx_fixture_tags_tag_fixture
  ON fixture_tags(tag, benchmark_name, fixture_id);
CREATE INDEX idx_fixture_tags_benchmark_tag
  ON fixture_tags(benchmark_name, tag);
CREATE INDEX idx_runs_model_timestamp
  ON runs(model_name, output_mode, timestamp);
CREATE INDEX idx_runs_version_timestamp
  ON runs(benchmark_suite_version, timestamp);
CREATE INDEX idx_models_grouping
  ON models(provider, base_model, reasoning_level, output_mode);
CREATE INDEX idx_benchmark_summaries_model_benchmark
  ON benchmark_summaries(model_name, output_mode, benchmark_name);
CREATE INDEX idx_benchmark_summaries_benchmark_model
  ON benchmark_summaries(benchmark_name, model_name, output_mode);
CREATE INDEX idx_benchmark_summaries_leaderboard
  ON benchmark_summaries(benchmark_name, pass_at_k DESC, avg_similarity DESC, model_name, output_mode);
CREATE INDEX idx_base_model_group_levels_group_level
  ON base_model_group_levels(group_id, level);
