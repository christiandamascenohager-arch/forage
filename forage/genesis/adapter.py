"""Narrow, auditable adapter between Gênesis and the Forage runtime.

This boundary deliberately exposes economic state and controlled ledger operations
without granting Gênesis direct access to Forage internals or live trading.
"""

from pathlib import Path
from typing import Any

from forage.agent.survival import SurvivalEngine
from forage.economy.ledger import Ledger
from forage.economy.revenue import RevenueEngine
from forage.economy.wallet import Wallet
from forage.evolution.engine import EvolutionEngine
from forage.infra.config import load_config
from forage.infra.database import init_db
from forage.safety.audit import AuditLog
from forage.safety.limits import SpendingLimiter


class ForageEconomicAdapter:
    """Controlled integration surface for the Gênesis orchestration layer."""

    def __init__(self, config_path: Path):
        self.config_path = Path(config_path).resolve()
        self.config = load_config(self.config_path)
        init_db(self.config)
        self.audit = AuditLog(self.config)
        self.ledger = Ledger(self.config)
        self.limiter = SpendingLimiter(self.config)
        self.wallet = Wallet(self.config, self.ledger, self.limiter)
        self.revenue = RevenueEngine(self.config, self.ledger)
        self.survival = SurvivalEngine(self.config, self.wallet, self.ledger)

    def get_balance(self) -> float:
        return self.wallet.balance

    def get_runway(self) -> float:
        return self.wallet.runway_days()

    def get_vitals(self) -> dict[str, Any]:
        return self.survival.check_vitals()

    def evaluate_survival(self) -> dict[str, Any]:
        vitals = self.get_vitals()
        return {
            "alive": vitals["is_alive"],
            "threat_level": vitals["threat_level"],
            "stress": vitals["stress"],
            "goal_priority": vitals["goal_priority"],
            "runway_days": vitals["runway_days"],
        }

    def record_expense(self, amount: float, description: str) -> dict[str, Any]:
        """Record a bounded expense through Forage's spending policy."""
        if amount <= 0:
            raise ValueError("Expense amount must be positive")
        result = self.wallet.spend(amount, description)
        self.audit.log(
            "genesis_expense",
            description,
            cost_usd=amount if result.success else 0,
            details={"allowed": result.success, "reason": result.reason},
        )
        return {
            "success": result.success,
            "balance_after": result.balance_after,
            "reason": result.reason,
        }

    def record_revenue(self, amount: float, source: str) -> dict[str, Any]:
        """Record revenue and apply the configured owner/reinvest/reserve split."""
        if amount <= 0:
            raise ValueError("Revenue amount must be positive")
        split = self.revenue.process_revenue(amount, source)
        self.audit.log(
            "genesis_revenue",
            f"Revenue recorded: {source}",
            revenue_usd=amount,
            details={
                "milestone": split.milestone_name,
                "owner": split.owner_share,
                "reinvest": split.reinvest_share,
                "reserve": split.reserve_share,
            },
        )
        return {
            "gross": split.gross,
            "owner": split.owner_share,
            "reinvest": split.reinvest_share,
            "reserve": split.reserve_share,
            "milestone": split.milestone_name,
            "balance_after": self.get_balance(),
        }

    def allocate_revenue(self, amount: float, source: str) -> dict[str, Any]:
        """Alias kept for the Gênesis economic contract."""
        return self.record_revenue(amount, source)

    def propose_evolution(self) -> dict[str, Any]:
        """Inspect whether Forage's evolution cycle is due; does not mutate state."""
        engine = EvolutionEngine.from_agent(_AdapterAgentView(self))
        return {
            "enabled": self.config.evolution.enabled,
            "due": engine.should_evolve(),
            "strategy": self.config.evolution.strategy,
        }

    def record_audit_event(self, action_type: str, message: str, **details: Any) -> None:
        self.audit.log(action_type, message, details=details or None)


class _AdapterAgentView:
    """Minimal internal view required by EvolutionEngine.from_agent."""

    def __init__(self, adapter: ForageEconomicAdapter):
        self.config = adapter.config
        self.ledger = adapter.ledger
        self.memory = _NoMemory()
        self.llm = None
        self.survival = adapter.survival
        self.audit = adapter.audit


class _NoMemory:
    """Placeholder: propose_evolution only calls should_evolve()."""

    pass
