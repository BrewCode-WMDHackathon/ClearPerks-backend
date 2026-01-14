"""
SLM Classifier - Extracts domain tags and signals from text.

This simulates a Fine-Tuned Small Language Model (SLM) for text classification.
In production, this would load an ONNX model or call a local inference server.

Now updated to extract domain-level tags and signals instead of UI categories.
"""

import random
from typing import Dict, List, Any

from app.core.domain_tags import (
    DomainTag,
    Signal,
    KEYWORD_TO_DOMAIN_TAG,
    SIGNAL_KEYWORDS,
)


class SLMClassifier:
    """Extracts domain tags and signals from text content."""
    
    MODEL_NAME = "ClearPerks-Phi3-Mini-4k-Instruct-Quantized"
    
    @staticmethod
    def classify_text(text: str) -> Dict[str, Any]:
        """
        Extract domain tags and signals from input text.
        
        This replaces the old UI-category classification with domain-level extraction.
        The UI category is now derived at runtime by CategoryService.
        
        Args:
            text: The text to classify (e.g., notification body, trend summary)
            
        Returns:
            dict with:
                - domain_tags: List of domain tag strings (e.g., ["HSA", "FSA"])
                - signals: Dict of signal flags (e.g., {"has_deadline": True})
                - priority: "high" | "medium" | "low"
                - confidence: float 0-1
                - model: model name
                - category: DEPRECATED legacy field for backward compatibility
        """
        text_lower = text.lower()
        
        # Extract domain tags from keywords
        domain_tags: List[str] = []
        for keyword, tag in KEYWORD_TO_DOMAIN_TAG.items():
            if keyword in text_lower and tag.value not in domain_tags:
                domain_tags.append(tag.value)
        
        # Default to BENEFITS_GENERAL if no specific tags found
        if not domain_tags:
            domain_tags.append(DomainTag.BENEFITS_GENERAL.value)
        
        # Extract signals from keywords
        signals: Dict[str, bool] = {}
        for signal, keywords in SIGNAL_KEYWORDS.items():
            if any(kw in text_lower for kw in keywords):
                signals[signal.value] = True
        
        # Derive priority from signals
        priority = "medium"
        if signals.get(Signal.URGENT.value) or signals.get(Signal.ACTION_REQUIRED.value):
            priority = "high"
        elif signals.get(Signal.HAS_DEADLINE.value):
            priority = "medium"
        
        # Confidence based on number of matches (simulated)
        base_confidence = 0.70
        tag_boost = min(len(domain_tags) * 0.05, 0.15)
        signal_boost = min(len(signals) * 0.03, 0.10)
        random_factor = random.random() * 0.05
        confidence = min(base_confidence + tag_boost + signal_boost + random_factor, 0.99)
        
        # Legacy category mapping for backward compatibility
        # This will be removed in future versions
        legacy_category = SLMClassifier._derive_legacy_category(domain_tags, signals)
        
        return {
            "domain_tags": domain_tags,
            "signals": signals,
            "priority": priority,
            "confidence": round(confidence, 4),
            "model": SLMClassifier.MODEL_NAME,
            # DEPRECATED: Legacy field for backward compatibility
            "category": legacy_category,
        }
    
    @staticmethod
    def _derive_legacy_category(domain_tags: List[str], signals: Dict[str, bool]) -> str:
        """
        Derive legacy category for backward compatibility.
        DEPRECATED: This will be removed when frontend migrates.
        """
        # Map domain tags to old category values
        tag_to_legacy = {
            "TAX": "gov",
            "HSA": "news",
            "FSA": "news",
            "401K": "news",
            "PTO": "news",
            "INSURANCE": "news",
            "PAYROLL": "news",
        }
        
        for tag in domain_tags:
            if tag in tag_to_legacy:
                return tag_to_legacy[tag]
        
        return "news"  # Default
    
    @staticmethod
    def compute_relevance_components(text: str, signals: Dict[str, bool]) -> Dict[str, float]:
        """
        Compute relevance score components for the given text.
        
        Returns:
            Dict with freshness, urgency, money, confidence scores (0-10 each)
        """
        # Urgency score from signals
        urgency = 0.0
        if signals.get(Signal.URGENT.value):
            urgency += 4.0
        if signals.get(Signal.ACTION_REQUIRED.value):
            urgency += 3.0
        if signals.get(Signal.HAS_DEADLINE.value):
            urgency += 2.0
        urgency = min(urgency, 10.0)
        
        # Money score from signals
        money = 0.0
        if signals.get(Signal.SAVES_MONEY.value):
            money += 5.0
        # Check for dollar amounts in text
        if "$" in text or "save" in text.lower():
            money += 3.0
        money = min(money, 10.0)
        
        # Confidence is already computed by classify_text
        confidence = 7.0  # Base confidence score
        
        # Freshness is typically computed based on created_at, not text
        # Return 0 here, to be filled in by the caller
        freshness = 0.0
        
        return {
            "freshness_score": freshness,
            "urgency_score": urgency,
            "money_score": money,
            "confidence_score": confidence,
        }

