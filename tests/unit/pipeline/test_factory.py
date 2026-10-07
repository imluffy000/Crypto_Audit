"""Pipeline factory tests."""

import pytest

from cryptoaudit.config.settings import Settings
from cryptoaudit.pipeline.factory import build_sandbox, build_strategies, parse_strategy_ids
from cryptoaudit.repair import StrategyId
from cryptoaudit.utils.errors import CryptoAuditError
from cryptoaudit.validation import DockerSandbox


def test_parse_strategy_ids():
    assert parse_strategy_ids(["s1,S2", "S2", " s4 "]) == [StrategyId.S1, StrategyId.S2, StrategyId.S4]
    with pytest.raises(CryptoAuditError):
        parse_strategy_ids(["S9"])


def test_build_strategies_wires_llm_settings():
    settings = Settings(llm_model="m:7b", llm_seed=42)
    strategies = build_strategies([StrategyId.S2, StrategyId.S3, StrategyId.S4], settings)
    assert [s.strategy_id for s in strategies] == [StrategyId.S2, StrategyId.S3, StrategyId.S4]
    assert strategies[1].model == "m:7b" and strategies[1].seed == 42
    assert strategies[1].client is strategies[2].client


def test_sandbox_defaults_to_docker_and_local_needs_opt_in():
    assert isinstance(build_sandbox(Settings()), DockerSandbox)
    with pytest.raises(CryptoAuditError):
        build_sandbox(Settings(), "local")
    assert build_sandbox(Settings(), "local", allow_unsafe_local=True).name == "local"
