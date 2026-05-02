"""Benchmark base classes for GitBench."""

from abc import ABC, abstractmethod

from gitbench.harness.types import Fixture, Score

from gitbench.benchmarks.stash_recovery import Benchmark, StashRecoveryBenchmark
from gitbench.benchmarks.commit_squash import CommitSquashBenchmark
from gitbench.benchmarks.tag_management import TagManagementBenchmark
from gitbench.benchmarks.git_clean import GitCleanBenchmark
from gitbench.benchmarks.git_grep import GitGrepBenchmark
from gitbench.benchmarks.git_log_format import GitLogFormatBenchmark
from gitbench.benchmarks.blame_forensics import BlameForensicsBenchmark
from gitbench.benchmarks.worktree_usage import WorktreeUsageBenchmark

__all__ = ["Benchmark", "StashRecoveryBenchmark", "CommitSquashBenchmark", "TagManagementBenchmark", "GitCleanBenchmark", "GitGrepBenchmark", "GitLogFormatBenchmark", "BlameForensicsBenchmark", "WorktreeUsageBenchmark"]
