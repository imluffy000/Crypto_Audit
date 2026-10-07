"""Rule registry: maps rule IDs to implementations and loads configs/rules.yaml."""

from pathlib import Path
from typing import Dict, List, Optional, Type, Union

import yaml

from cryptoaudit.config.settings import Settings
from cryptoaudit.models.analysis import RuleConfig
from cryptoaudit.rules.base import BaseRule
from cryptoaudit.rules.cr1_weak_hash import CR1Rule
from cryptoaudit.rules.cr2_unsafe_cipher import CR2Rule
from cryptoaudit.rules.cr3_iv_nonce import CR3Rule
from cryptoaudit.rules.cr4_kdf import CR4Rule
from cryptoaudit.rules.cr5_insecure_random import CR5Rule
from cryptoaudit.utils.errors import CryptoAuditError, ErrorCode

RULE_CLASS_MAP: Dict[str, Type[BaseRule]] = {
    "CR1": CR1Rule,
    "CR2": CR2Rule,
    "CR3": CR3Rule,
    "CR4": CR4Rule,
    "CR5": CR5Rule,
}

# Repository-level rules file (src/cryptoaudit/rules/registry.py -> repo root).
REPO_RULES_FILE = Path(__file__).resolve().parents[3] / "configs" / "rules.yaml"


def resolve_rules_file(rules_file: Optional[Path] = None) -> Path:
    """
    Resolve the rules file independent of the current working directory.

    Order: explicit argument, then Settings.rules_file (cwd-relative), then the
    repository's configs/rules.yaml.
    """
    if rules_file is not None:
        return Path(rules_file)
    configured = Settings().rules_file
    if configured.is_file():
        return configured
    return REPO_RULES_FILE


def load_rule_configs(rules_file: Union[str, Path]) -> List[RuleConfig]:
    """Safely load and validate the rule configuration file."""
    path = Path(rules_file)
    if not path.is_file():
        raise CryptoAuditError(ErrorCode.ANALYSIS_ERROR, f"Rule configuration file not found: {path}", {"rules_file": str(path)})
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("rules"), list):
        raise CryptoAuditError(ErrorCode.ANALYSIS_ERROR, f"Invalid rule configuration in {path}: expected a 'rules' list")
    return [RuleConfig(**entry) for entry in data["rules"]]


def load_default_rules(rules_file: Optional[Path] = None) -> List[BaseRule]:
    """Instantiate every configured rule; fail loudly instead of silently loading no rules."""
    path = resolve_rules_file(rules_file)
    configs = load_rule_configs(path)
    configured_ids = {config.rule_id for config in configs}
    missing = sorted(set(RULE_CLASS_MAP) - configured_ids)
    if missing:
        raise CryptoAuditError(
            ErrorCode.ANALYSIS_ERROR,
            f"Rule configuration {path} is missing rules: {', '.join(missing)}",
            {"rules_file": str(path), "missing": missing},
        )
    return [RULE_CLASS_MAP[config.rule_id](config) for config in configs if config.rule_id in RULE_CLASS_MAP]
