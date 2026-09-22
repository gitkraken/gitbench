"""Effort acceptance and observed reasoning are separate preflight signals."""

import io
import json
import urllib.error
from unittest.mock import patch

import click
import pytest

from gitbench.cli import (
    EffortPreflightTarget,
    _call_responses_api,
    _check_reasoning_evidence,
    _discover_effort_preflight_targets,
    _run_effort_preflights,
)
from gitbench.harness.capabilities import load_effort_matrix, save_effort_mapping


@pytest.fixture
def matrix_path(tmp_path, monkeypatch):
    path = tmp_path / "effort_matrix.json"
    monkeypatch.setattr("gitbench.harness.capabilities._EFFORT_MATRIX_PATH", path)
    return path


@pytest.fixture
def target():
    return EffortPreflightTarget(
        profile_name="test", model="anthropic/claude-fable-5.1:low",
        base_model="anthropic/claude-fable-5.1", requested_effort="low",
        provider="openai", base_url="https://openrouter.ai/api/v1",
        api_key=None, timeout=30,
    )


@pytest.mark.parametrize("tokens", [None, 0])
def test_absent_reasoning_warns_and_remains_unverified(matrix_path, target, capsys, tokens):
    body = {"reasoning": {"effort": "low"}, "output": [{"type": "message"}]}
    if tokens is not None:
        body["usage"] = {"output_tokens_details": {"reasoning_tokens": tokens}}
    assert _check_reasoning_evidence(body) == (False, tokens, False)
    with patch("gitbench.cli._call_responses_api", return_value=body), \
         patch("gitbench.cli.time.sleep"):
        _run_effort_preflights([target])
    assert "reasoning not observed (unverified); continuing" in capsys.readouterr().err
    entry = json.loads(matrix_path.read_text())["models"][target.base_model.split("/")[1]]
    assert entry["mappings"]["low"] == "low"
    assert entry["verification"]["low"] == "unverified"
    assert load_effort_matrix() == {}
    targets = _discover_effort_preflight_targets(
        [("test", {"base_url": target.base_url}, [target.model])],
        base_url_override=None, provider_override=None, timeout_override=None,
    )
    assert len(targets) == 1


@pytest.mark.parametrize("evidence", [
    {"output": [{"type": "reasoning"}]},
    {"usage": {"output_tokens_details": {"reasoning_tokens": 8}}},
])
def test_reasoning_evidence_verifies_mapping(matrix_path, target, evidence):
    body = {"reasoning": {"effort": "medium"}, **evidence}
    with patch("gitbench.cli._call_responses_api", return_value=body) as call:
        _run_effort_preflights([target])
    assert call.call_count == 1
    assert load_effort_matrix() == {"claude-fable-5.1": {"low": "medium"}}


def test_explicit_rejection_fails_without_caching(matrix_path, target):
    error = {"error": {"message": "Unsupported reasoning effort: low"}}
    with patch("gitbench.cli._call_responses_api", return_value=error), \
         patch("gitbench.cli.time.sleep"), \
         pytest.raises(click.ClickException, match="Unsupported reasoning effort: low"):
        _run_effort_preflights([target])
    assert not matrix_path.exists()


def test_later_transport_failure_preserves_reported_mapping(matrix_path, target):
    body = {"reasoning": {"effort": "low"}}
    with patch("gitbench.cli._call_responses_api", side_effect=[body, None, None]), \
         patch("gitbench.cli.time.sleep"):
        _run_effort_preflights([target])
    entry = json.loads(matrix_path.read_text())["models"]["claude-fable-5.1"]
    assert entry["verification"]["low"] == "unverified"


def test_http_rejection_body_is_preserved():
    body = {"error": {"message": "Unsupported reasoning effort: low"}}
    error = urllib.error.HTTPError(
        "https://example.test/responses", 400, "Bad Request", {},
        io.BytesIO(json.dumps(body).encode()),
    )
    with patch("gitbench.cli.urllib.request.urlopen", side_effect=error):
        assert _call_responses_api("https://example.test", "model", "low", "test", None, 30) == body


def test_unverified_mapping_does_not_hide_other_verified_levels(matrix_path):
    save_effort_mapping("model", "high", "high")
    save_effort_mapping("model", "low", "low", verification="unverified")
    assert load_effort_matrix() == {"model": {"high": "high"}}
    save_effort_mapping("model", "low", "low", verification="verified")
    assert load_effort_matrix() == {"model": {"high": "high", "low": "low"}}
