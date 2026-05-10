"""Fixture loader for GitBench benchmarks."""

import logging
import os
from pathlib import Path
from typing import Any

import yaml

from gitbench.harness.types import Fixture

logger = logging.getLogger(__name__)

REQUIRED_FIELDS = ("id", "setup", "prompt", "expected")
ALLOWED_DIFFICULTIES = {"trivial", "easy", "medium", "hard", "expert"}
METADATA_FIELDS = ("purpose", "difficulty", "tags")


class FixtureLoader:
    """Loads and validates fixture files for benchmarking."""

    def load_file(self, path: str) -> list[Fixture]:
        """Parse a single YAML fixture file.

        Args:
            path: Path to the YAML fixture file.

        Returns:
            List of Fixture objects parsed from the file.

        Raises:
            FileNotFoundError: If the file does not exist.
            ValueError: If a fixture is missing required fields or has invalid structure.
        """
        file_path = Path(path)
        if not file_path.exists():
            raise FileNotFoundError(f"Fixture file not found: {path}")

        with open(file_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if data is None:
            logger.warning(f"Empty fixture file: {path}")
            return []

        # Support both single fixture (dict) and list of fixtures
        if isinstance(data, dict):
            fixtures = [data]
        elif isinstance(data, list):
            fixtures = data
        else:
            raise ValueError(f"Invalid fixture format in {path}: expected dict or list")

        results: list[Fixture] = []
        for idx, fixture_data in enumerate(fixtures):
            try:
                results.append(self._parse_fixture(fixture_data, path, idx))
            except ValueError as e:
                raise ValueError(f"Error in fixture at index {idx} of {path}: {e}") from e

        return results

    def _parse_fixture(self, data: Any, source: str, index: int) -> Fixture:
        """Parse and validate a single fixture dict.

        Args:
            data: Raw fixture dictionary.
            source: Source file path for error messages.
            index: Fixture index in file for error messages.

        Returns:
            Validated Fixture object.

        Raises:
            ValueError: If required fields are missing or types are wrong.
        """
        if not isinstance(data, dict):
            raise ValueError(f"Expected dict, got {type(data).__name__}")

        # Check required fields
        for field in REQUIRED_FIELDS:
            if field not in data:
                raise ValueError(
                    f"Missing required field '{field}' in fixture {index} of {source}"
                )

        fixture_id = data["id"]
        if not isinstance(fixture_id, str) or not fixture_id.strip():
            raise ValueError(f"Fixture id must be a non-empty string in {source}:{index}")

        setup = data["setup"]
        if not isinstance(setup, list):
            raise ValueError(
                f"Fixture '{fixture_id}': 'setup' must be a list of strings"
            )
        for cmd in setup:
            if not isinstance(cmd, str):
                raise ValueError(
                    f"Fixture '{fixture_id}': each setup command must be a string"
                )

        prompt = data["prompt"]
        if not isinstance(prompt, str):
            raise ValueError(f"Fixture '{fixture_id}': 'prompt' must be a string")

        expected = data["expected"]
        if not isinstance(expected, str):
            raise ValueError(f"Fixture '{fixture_id}': 'expected' must be a string")

        scoring = data.get("scoring", {"type": "similarity", "threshold": 0.5})
        if not isinstance(scoring, dict):
            raise ValueError(
                f"Fixture '{fixture_id}': 'scoring' must be a dict"
            )

        description = data.get("description", "")

        # Parse optional metadata fields
        purpose = data.get("purpose", "")
        difficulty = data.get("difficulty", "")
        tags = data.get("tags", [])

        # Soft validation: warn if metadata fields are missing
        missing = [f for f in METADATA_FIELDS if f not in data]
        if missing:
            logger.warning(
                "Fixture '%s' in %s is missing metadata fields: %s",
                fixture_id, source, ", ".join(missing),
            )

        # Validate difficulty is in allowed enum
        if difficulty and difficulty not in ALLOWED_DIFFICULTIES:
            logger.warning(
                "Fixture '%s': invalid difficulty '%s' (allowed: %s). Treating as empty.",
                fixture_id, difficulty, ", ".join(sorted(ALLOWED_DIFFICULTIES)),
            )
            difficulty = ""

        # Validate tags is a list of strings
        if not isinstance(tags, list):
            logger.warning(
                "Fixture '%s': 'tags' must be a list of strings, got %s",
                fixture_id, type(tags).__name__,
            )
            tags = []
        else:
            for t in tags:
                if not isinstance(t, str):
                    logger.warning(
                        "Fixture '%s': each tag must be a string, got %s",
                        fixture_id, type(t).__name__,
                    )
                    tags = [str(t) for t in tags]
                    break

        return Fixture(
            id=fixture_id,
            description=description,
            setup=setup,
            prompt=prompt,
            expected=expected,
            scoring=scoring,
            purpose=purpose,
            difficulty=difficulty,
            tags=tags,
        )

    def load_dir(self, dirpath: str) -> list[Fixture]:
        """Load all YAML fixtures from a directory.

        Args:
            dirpath: Path to the directory containing fixture files.

        Returns:
            Combined list of all Fixture objects from all .yaml files.

        Raises:
            FileNotFoundError: If the directory does not exist.
        """
        dir_path = Path(dirpath)
        if not dir_path.is_dir():
            raise FileNotFoundError(f"Fixture directory not found: {dirpath}")

        all_fixtures: list[Fixture] = []

        for file_path in sorted(dir_path.iterdir()):
            if file_path.suffix.lower() in (".yaml", ".yml"):
                logger.debug(f"Loading fixtures from: {file_path}")
                try:
                    fixtures = self.load_file(str(file_path))
                    all_fixtures.extend(fixtures)
                except Exception as e:
                    logger.error(f"Failed to load {file_path}: {e}")
                    raise

        return all_fixtures
