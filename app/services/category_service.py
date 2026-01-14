"""
Category Service for deriving UI categories from domain tags and signals.

This service implements the core principle: UI categories are DERIVED at runtime,
never stored directly in the database.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from app.core.domain_tags import (
    DomainTag,
    Signal,
    UICategory,
    DOMAIN_TAG_TO_UI_CATEGORY,
)


class CategoryService:
    """Derives UI categories and computes relevance from domain tags and signals."""

    @staticmethod
    def derive_ui_category(domain_tags: List[str], signals: Dict[str, Any] = None) -> str:
        """
        Derive UI category from domain tags.

        Priority Rules:
        1. First matching domain tag determines category
        2. Fallback to "All" if no match

        Note: "Deadlines" is a cross-cutting VIEW, not an exclusive category.
        Content with has_deadline signal appears in Deadlines tab regardless of category.

        Args:
            domain_tags: List of domain tag strings (e.g., ["HSA", "FSA"])
            signals: Optional dict of signals (not used for main category, but kept for future)

        Returns:
            UI category string (e.g., "Health", "Pay", "Retirement")
        """
        if not domain_tags:
            return UICategory.ALL.value

        for tag_str in domain_tags:
            try:
                tag = DomainTag(tag_str)
                if tag in DOMAIN_TAG_TO_UI_CATEGORY:
                    return DOMAIN_TAG_TO_UI_CATEGORY[tag].value
            except ValueError:
                # Unknown tag, continue to next
                continue

        return UICategory.ALL.value

    @staticmethod
    def compute_urgency_level(
        signals: Dict[str, Any] = None,
        priority: str = None,
        deadline_date: datetime = None
    ) -> str:
        """
        Derive urgency level from signals and priority.

        Returns:
            "high", "medium", or "normal"
        """
        signals = signals or {}

        # High urgency: explicit urgent/action_required signals
        if signals.get(Signal.URGENT.value) or signals.get(Signal.ACTION_REQUIRED.value):
            return "high"

        # High urgency: priority is high
        if priority and priority.lower() == "high":
            return "high"

        # Medium urgency: has deadline within 30 days
        if signals.get(Signal.HAS_DEADLINE.value):
            if deadline_date:
                days_until = (deadline_date - datetime.utcnow()).days
                if days_until <= 7:
                    return "high"
                elif days_until <= 30:
                    return "medium"
            return "medium"

        return "normal"

    @staticmethod
    def is_deadline_eligible(
        signals: Dict[str, Any] = None,
        deadline_date: datetime = None
    ) -> bool:
        """
        Check if content should appear in the Deadlines tab.

        Content is deadline-eligible if:
        - has_deadline signal is True, OR
        - deadline_date is set and in the future
        """
        signals = signals or {}

        if signals.get(Signal.HAS_DEADLINE.value):
            return True

        if deadline_date and deadline_date > datetime.utcnow():
            return True

        return False

    @staticmethod
    def compute_relevance_score(
        freshness_score: float = 0,
        urgency_score: float = 0,
        money_score: float = 0,
        confidence_score: float = 0,
        user_fit_score: float = 0
    ) -> float:
        """
        Compute composite relevance score.

        Each component score should be normalized 0-10.
        Total relevance is sum of all components (0-50 range).

        Args:
            freshness_score: How recent the content is (0-10)
            urgency_score: How urgent/time-sensitive (0-10)
            money_score: Potential money savings (0-10)
            confidence_score: Classification confidence (0-10)
            user_fit_score: Optional personalization score (0-10)

        Returns:
            Composite relevance score (0-50)
        """
        return (
            freshness_score +
            urgency_score +
            money_score +
            confidence_score +
            (user_fit_score or 0)
        )

    @staticmethod
    def compute_freshness_score(created_at: datetime, max_age_days: int = 30) -> float:
        """
        Compute freshness score based on content age.

        Returns 10 for brand new content, decaying to 0 over max_age_days.
        """
        if not created_at:
            return 0

        age = datetime.utcnow() - created_at
        age_days = age.days

        if age_days <= 0:
            return 10.0
        elif age_days >= max_age_days:
            return 0.0
        else:
            # Linear decay
            return 10.0 * (1 - age_days / max_age_days)

    @staticmethod
    def compute_urgency_score(
        signals: Dict[str, Any] = None,
        deadline_date: datetime = None
    ) -> float:
        """
        Compute urgency score from signals and deadline proximity.

        Returns 0-10 based on urgency factors.
        """
        signals = signals or {}
        score = 0.0

        # Urgent signal: +4
        if signals.get(Signal.URGENT.value):
            score += 4.0

        # Action required: +3
        if signals.get(Signal.ACTION_REQUIRED.value):
            score += 3.0

        # Deadline proximity
        if signals.get(Signal.HAS_DEADLINE.value) or deadline_date:
            if deadline_date:
                days_until = (deadline_date - datetime.utcnow()).days
                if days_until <= 3:
                    score += 3.0
                elif days_until <= 7:
                    score += 2.0
                elif days_until <= 14:
                    score += 1.0
            else:
                score += 1.0  # Has deadline but no specific date

        return min(score, 10.0)

    @staticmethod
    def compute_money_score(
        signals: Dict[str, Any] = None,
        estimated_savings: float = None
    ) -> float:
        """
        Compute money score from savings signals and amounts.

        Returns 0-10 based on savings potential.
        """
        signals = signals or {}
        score = 0.0

        # Saves money signal: +3
        if signals.get(Signal.SAVES_MONEY.value):
            score += 3.0

        # Estimated savings amount
        if estimated_savings:
            if estimated_savings >= 1000:
                score += 7.0
            elif estimated_savings >= 500:
                score += 5.0
            elif estimated_savings >= 100:
                score += 3.0
            else:
                score += 1.0

        return min(score, 10.0)

    @staticmethod
    def enrich_response(
        obj: Any,
        domain_tags: List[str] = None,
        signals: Dict[str, Any] = None,
        priority: str = None,
        deadline_date: datetime = None
    ) -> Dict[str, Any]:
        """
        Enrich a response object with derived fields.

        Adds:
        - ui_category: Derived from domain_tags
        - urgency_level: Derived from signals and priority
        - is_deadline: Whether it appears in Deadlines tab

        Args:
            obj: The object to enrich (dict or ORM model)
            domain_tags: List of domain tag strings
            signals: Dict of signals
            priority: Priority string
            deadline_date: Optional deadline datetime

        Returns:
            Dict with original fields plus derived fields
        """
        domain_tags = domain_tags or []
        signals = signals or {}

        # Convert ORM object to dict if needed
        if hasattr(obj, "__dict__"):
            result = {k: v for k, v in obj.__dict__.items() if not k.startswith("_")}
        elif hasattr(obj, "dict"):
            result = obj.dict()
        else:
            result = dict(obj)

        # Add derived fields
        result["ui_category"] = CategoryService.derive_ui_category(domain_tags, signals)
        result["urgency_level"] = CategoryService.compute_urgency_level(signals, priority, deadline_date)
        result["is_deadline"] = CategoryService.is_deadline_eligible(signals, deadline_date)

        return result
