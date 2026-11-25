"""Scenario loader and YAML parser for the benchmark catalog."""

from __future__ import annotations

import glob
import os
from pathlib import Path
from typing import Dict, List, Optional
import yaml
from ar_biz_agent_eval.core.models import SessionState
from ar_biz_agent_eval.core.registry import ScenarioRegistry, scenario_registry
from ar_biz_agent_eval.core.scenario import Scenario


def get_default_scenarios_dir() -> Path:
    """Return the absolute path to packaged scenario YAMLs."""
    return Path(__file__).parent / "data"


def load_scenario_from_file(file_path: str | Path, registry: Optional[ScenarioRegistry] = None) -> Scenario:
    """Load and validate a single scenario YAML or JSON file."""
    path = Path(file_path)
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    scenario = Scenario.model_validate(data)
    target_registry = registry or scenario_registry
    target_registry.register(scenario)
    return scenario


def load_all_scenarios(
    directory: Optional[str | Path] = None,
    registry: Optional[ScenarioRegistry] = None,
) -> List[Scenario]:
    """Load and register all benchmark scenarios from target directory."""
    target_dir = Path(directory) if directory else get_default_scenarios_dir()
    target_registry = registry or scenario_registry
    scenarios: List[Scenario] = []

    if not target_dir.exists():
        return scenarios

    for ext in ("*.yaml", "*.yml", "*.json"):
        for file_path in target_dir.glob(ext):
            try:
                scen = load_scenario_from_file(file_path, registry=target_registry)
                scenarios.append(scen)
            except Exception as e:
                print(f"[Warning] Failed to load scenario from {file_path}: {e}")

    return scenarios


class ScenarioLoader:
    """Helper class to discover and load scenarios into registry."""

    def __init__(self, registry: Optional[ScenarioRegistry] = None, scenarios_dir: Optional[str | Path] = None) -> None:
        self.registry = registry or scenario_registry
        self.scenarios_dir = Path(scenarios_dir) if scenarios_dir else get_default_scenarios_dir()

    def load_builtin_scenarios(self) -> int:
        scenarios = load_all_scenarios(directory=self.scenarios_dir, registry=self.registry)
        return len(scenarios)

    def load_scenario_from_file(self, file_path: str | Path) -> Scenario:
        return load_scenario_from_file(file_path, registry=self.registry)
