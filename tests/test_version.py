"""Tests for artifact version constants."""

from gitbench.version import BENCHMARK_SUITE_VERSION


def test_benchmark_suite_version_reflects_f010_semantic_change():
    assert BENCHMARK_SUITE_VERSION == "0.3.1"
