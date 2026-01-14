"""
Domain Tags, Signals, and UI Category definitions for ClearPerks.

This module defines the domain-driven architecture where:
- Domain tags represent benefit types (HSA, FSA, 401K, etc.)
- Signals represent flags/attributes (has_deadline, saves_money, etc.)
- UI categories are DERIVED at runtime from domain tags and signals
"""

from enum import Enum
from typing import Dict


class DomainTag(str, Enum):
    """Domain-level benefit category tags stored in the database."""
    HSA = "HSA"
    FSA = "FSA"
    K401 = "401K"
    PTO = "PTO"
    INSURANCE = "INSURANCE"
    PAYROLL = "PAYROLL"
    TAX = "TAX"
    DEDUCTIBLE = "DEDUCTIBLE"
    BENEFITS_GENERAL = "BENEFITS_GENERAL"


class Signal(str, Enum):
    """Signals/flags that can be attached to content."""
    HAS_DEADLINE = "has_deadline"
    SAVES_MONEY = "saves_money"
    POLICY_CHANGE = "policy_change"
    URGENT = "urgent"
    ACTION_REQUIRED = "action_required"


class UICategory(str, Enum):
    """UI-visible categories derived at runtime."""
    ALL = "All"
    PAY = "Pay"
    HEALTH = "Health"
    RETIREMENT = "Retirement"
    TIME_OFF = "Time Off"
    DEADLINES = "Deadlines"


# Mapping: DomainTag → UICategory
DOMAIN_TAG_TO_UI_CATEGORY: Dict[DomainTag, UICategory] = {
    DomainTag.HSA: UICategory.HEALTH,
    DomainTag.FSA: UICategory.HEALTH,
    DomainTag.INSURANCE: UICategory.HEALTH,
    DomainTag.DEDUCTIBLE: UICategory.HEALTH,
    DomainTag.K401: UICategory.RETIREMENT,
    DomainTag.PTO: UICategory.TIME_OFF,
    DomainTag.PAYROLL: UICategory.PAY,
    DomainTag.TAX: UICategory.PAY,
    DomainTag.BENEFITS_GENERAL: UICategory.ALL,
}


# Keyword mappings for classification
KEYWORD_TO_DOMAIN_TAG: Dict[str, DomainTag] = {
    "hsa": DomainTag.HSA,
    "health savings": DomainTag.HSA,
    "health savings account": DomainTag.HSA,
    "fsa": DomainTag.FSA,
    "flexible spending": DomainTag.FSA,
    "flexible spending account": DomainTag.FSA,
    "401k": DomainTag.K401,
    "401(k)": DomainTag.K401,
    "retirement": DomainTag.K401,
    "pension": DomainTag.K401,
    "pto": DomainTag.PTO,
    "vacation": DomainTag.PTO,
    "leave": DomainTag.PTO,
    "time off": DomainTag.PTO,
    "paid time off": DomainTag.PTO,
    "sick leave": DomainTag.PTO,
    "insurance": DomainTag.INSURANCE,
    "medical": DomainTag.INSURANCE,
    "dental": DomainTag.INSURANCE,
    "vision": DomainTag.INSURANCE,
    "health plan": DomainTag.INSURANCE,
    "payroll": DomainTag.PAYROLL,
    "salary": DomainTag.PAYROLL,
    "wage": DomainTag.PAYROLL,
    "pay period": DomainTag.PAYROLL,
    "tax": DomainTag.TAX,
    "irs": DomainTag.TAX,
    "w-2": DomainTag.TAX,
    "w2": DomainTag.TAX,
    "deductible": DomainTag.DEDUCTIBLE,
    "out of pocket": DomainTag.DEDUCTIBLE,
}


# Signal extraction keywords
SIGNAL_KEYWORDS: Dict[Signal, list] = {
    Signal.HAS_DEADLINE: ["deadline", "expires", "expiring", "due date", "by date", "end of year"],
    Signal.SAVES_MONEY: ["save", "savings", "optimize", "maximize", "tax-free", "tax advantage", "reduce cost"],
    Signal.POLICY_CHANGE: ["new policy", "policy change", "update", "amendment", "effective date"],
    Signal.URGENT: ["urgent", "immediately", "asap", "critical", "time-sensitive"],
    Signal.ACTION_REQUIRED: ["action required", "required action", "must", "need to", "please complete"],
}
