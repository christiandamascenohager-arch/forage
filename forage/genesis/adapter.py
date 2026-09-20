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
from datetime import datetime, timedelta, timezone

from forage.evolution.genome_store import GenomeStore
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
        store = GenomeStore(self.config)
        last = store.last_evolution_time()
        if not self.config.evolution.enabled:
            due = False
        elif last is None:
            due = True
        else:
            last_dt = datetime.fromisoformat(last).replace(tzinfo=timezone.utc)
            intervals = {"hourly": timedelta(hours=1), "daily": timedelta(days=1), "weekly": timedelta(weeks=1)}
            interval = intervals.get(self.config.evolution.cycle, timedelta(days=1))
            due = datetime.now(timezone.utc) - last_dt >= interval
        return {
            "enabled": self.config.evolution.enabled,
            "due": due,
            "strategy": self.config.evolution.strategy,
            "generation": store.get_generation(),
            "last_evolution": last,
        }

    def record_audit_event(self, action_type: str, message: str, **details: Any) -> None:
        self.audit.log(action_type, message, details=details or None)

