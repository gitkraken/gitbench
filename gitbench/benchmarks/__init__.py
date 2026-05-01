"""Benchmark base classes for GitBench."""

from abc import ABC, abstractmethod

from gitbench.harness.types import Fixture, Score

from gitbench.benchmarks.stash_recovery import Benchmark, StashRecoveryBenchmark
from gitbench.benchmarks.commit_squash import CommitSquashBenchmark
from gitbench.benchmarks.tag_management import TagManagementBenchmark
from gitbench.benchmarks.git_clean import GitCleanBenchmark
from gitbench.benchmarks.git_grep import GitGrepBenchmark

__all__ = ["Benchmark", "StashRecoveryBenchmark", "CommitSquashBenchmark", "TagManagementBenchmark", "GitCleanBenchmark", "GitGrepBenchmark"]
