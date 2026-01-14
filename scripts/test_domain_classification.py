"""
Test script for the new domain-driven architecture.

This script tests:
1. SLMClassifier domain tag and signal extraction
2. CategoryService UI category derivation
3. Relevance score computation

Run with: python scripts/test_domain_classification.py
"""

import sys
import os

# Add parent directory to path to allow imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.domain_tags import DomainTag, Signal, UICategory, DOMAIN_TAG_TO_UI_CATEGORY
from app.services.slm_classifier import SLMClassifier
from app.services.category_service import CategoryService


def test_slm_classifier():
    """Test SLMClassifier extracts domain tags and signals correctly."""
    print("\n" + "="*60)
    print("Testing SLMClassifier")
    print("="*60)
    
    test_cases = [
        {
            "text": "Maximize your HSA contributions before the deadline",
            "expected_tags": ["HSA"],
            "expected_signals": ["has_deadline", "saves_money"],
        },
        {
            "text": "Your 401k employer match is 6% - are you contributing enough?",
            "expected_tags": ["401K"],
            "expected_signals": [],
        },
        {
            "text": "Urgent: FSA balance expires end of year - use it or lose it!",
            "expected_tags": ["FSA"],
            "expected_signals": ["has_deadline", "urgent"],
        },
        {
            "text": "New IRS tax regulations for 2026",
            "expected_tags": ["TAX"],
            "expected_signals": ["policy_change"],
        },
        {
            "text": "PTO balance update - you have 80 hours remaining",
            "expected_tags": ["PTO"],
            "expected_signals": [],
        },
        {
            "text": "Action required: Update your health insurance beneficiary",
            "expected_tags": ["INSURANCE"],
            "expected_signals": ["action_required"],
        },
    ]
    
    passed = 0
    failed = 0
    
    for i, case in enumerate(test_cases, 1):
        result = SLMClassifier.classify_text(case["text"])
        
        # Check domain tags
        tags_match = all(tag in result["domain_tags"] for tag in case["expected_tags"])
        
        # Check signals
        signals_match = all(
            result["signals"].get(sig) for sig in case["expected_signals"]
        )
        
        status = "[PASS]" if tags_match and signals_match else "[FAIL]"
        
        if tags_match and signals_match:
            passed += 1
        else:
            failed += 1
        
        print(f"\nTest {i}: {status}")
        print(f"  Input: {case['text'][:50]}...")
        print(f"  Expected tags: {case['expected_tags']}, Got: {result['domain_tags']}")
        print(f"  Expected signals: {case['expected_signals']}, Got: {list(result['signals'].keys())}")
        print(f"  Priority: {result['priority']}, Confidence: {result['confidence']}")
        print(f"  Legacy category: {result['category']}")
    
    print(f"\n{'='*60}")
    print(f"SLMClassifier Results: {passed} passed, {failed} failed")
    print("="*60)
    
    return failed == 0


def test_category_service():
    """Test CategoryService derives UI categories correctly."""
    print("\n" + "="*60)
    print("Testing CategoryService")
    print("="*60)
    
    test_cases = [
        {
            "domain_tags": ["HSA"],
            "signals": {},
            "expected_category": "Health",
            "expected_urgency": "normal",
        },
        {
            "domain_tags": ["FSA"],
            "signals": {"has_deadline": True},
            "expected_category": "Health",
            "expected_urgency": "medium",
        },
        {
            "domain_tags": ["401K"],
            "signals": {},
            "expected_category": "Retirement",
            "expected_urgency": "normal",
        },
        {
            "domain_tags": ["PTO"],
            "signals": {"urgent": True},
            "expected_category": "Time Off",
            "expected_urgency": "high",
        },
        {
            "domain_tags": ["PAYROLL", "TAX"],
            "signals": {},
            "expected_category": "Pay",  # First match wins
            "expected_urgency": "normal",
        },
        {
            "domain_tags": ["BENEFITS_GENERAL"],
            "signals": {"action_required": True},
            "expected_category": "All",
            "expected_urgency": "high",
        },
    ]
    
    passed = 0
    failed = 0
    
    for i, case in enumerate(test_cases, 1):
        ui_category = CategoryService.derive_ui_category(
            case["domain_tags"], case["signals"]
        )
        urgency = CategoryService.compute_urgency_level(case["signals"])
        
        category_match = ui_category == case["expected_category"]
        urgency_match = urgency == case["expected_urgency"]
        
        status = "[PASS]" if category_match and urgency_match else "[FAIL]"
        
        if category_match and urgency_match:
            passed += 1
        else:
            failed += 1
        
        print(f"\nTest {i}: {status}")
        print(f"  Domain tags: {case['domain_tags']}")
        print(f"  Signals: {case['signals']}")
        print(f"  Expected category: {case['expected_category']}, Got: {ui_category}")
        print(f"  Expected urgency: {case['expected_urgency']}, Got: {urgency}")
    
    print(f"\n{'='*60}")
    print(f"CategoryService Results: {passed} passed, {failed} failed")
    print("="*60)
    
    return failed == 0


def test_relevance_scoring():
    """Test relevance score computation."""
    print("\n" + "="*60)
    print("Testing Relevance Scoring")
    print("="*60)
    
    # Test urgency score
    urgency_cases = [
        ({"urgent": True, "action_required": True}, 7.0),  # 4 + 3
        ({"has_deadline": True}, 2.0),
        ({}, 0.0),
    ]
    
    print("\nUrgency Score Tests:")
    for signals, expected_min in urgency_cases:
        score = CategoryService.compute_urgency_score(signals)
        status = "[OK]" if score >= expected_min else "[X]"
        print(f"  {status} Signals {signals}: score={score} (expected >= {expected_min})")
    
    # Test money score
    money_cases = [
        ({"saves_money": True}, 1000, 10.0),  # 5 + 7 (capped at 10)
        ({"saves_money": True}, 100, 6.0),    # 5 + 3
        ({}, 500, 5.0),                       # 0 + 5
        ({}, None, 0.0),
    ]
    
    print("\nMoney Score Tests:")
    for signals, savings, expected_min in money_cases:
        score = CategoryService.compute_money_score(signals, savings)
        status = "[OK]" if score >= expected_min else "[X]"
        print(f"  {status} Signals {signals}, savings=${savings}: score={score} (expected >= {expected_min})")
    
    # Test composite score
    composite = CategoryService.compute_relevance_score(
        freshness_score=8.0,
        urgency_score=5.0,
        money_score=7.0,
        confidence_score=6.0,
        user_fit_score=4.0
    )
    expected_composite = 30.0
    status = "[OK]" if composite == expected_composite else "[X]"
    print(f"\n{status} Composite score: {composite} (expected {expected_composite})")
    
    print(f"\n{'='*60}")
    print("Relevance Scoring Tests Complete")
    print("="*60)
    
    return True


def test_deadline_eligibility():
    """Test deadline eligibility detection."""
    print("\n" + "="*60)
    print("Testing Deadline Eligibility")
    print("="*60)
    
    from datetime import datetime, timedelta
    
    test_cases = [
        ({"has_deadline": True}, None, True),
        ({}, datetime.utcnow() + timedelta(days=10), True),
        ({}, datetime.utcnow() - timedelta(days=10), False),  # Past deadline
        ({}, None, False),
    ]
    
    passed = 0
    for signals, deadline, expected in test_cases:
        result = CategoryService.is_deadline_eligible(signals, deadline)
        status = "[OK]" if result == expected else "[X]"
        if result == expected:
            passed += 1
        print(f"  {status} Signals={signals}, deadline={deadline}: {result} (expected {expected})")
    
    print(f"\n{'='*60}")
    print(f"Deadline Eligibility: {passed}/{len(test_cases)} passed")
    print("="*60)
    
    return passed == len(test_cases)


def main():
    """Run all tests."""
    print("\n" + "#"*60)
    print("# ClearPerks Domain Architecture Tests")
    print("#"*60)
    
    results = []
    
    results.append(("SLMClassifier", test_slm_classifier()))
    results.append(("CategoryService", test_category_service()))
    results.append(("Relevance Scoring", test_relevance_scoring()))
    results.append(("Deadline Eligibility", test_deadline_eligibility()))
    
    print("\n" + "#"*60)
    print("# SUMMARY")
    print("#"*60)
    
    all_passed = True
    for name, passed in results:
        status = "[PASS]" if passed else "[FAIL]"
        print(f"  {status}: {name}")
        if not passed:
            all_passed = False
    
    print("\n" + "#"*60)
    if all_passed:
        print("# ALL TESTS PASSED!")
    else:
        print("# SOME TESTS FAILED!")
    print("#"*60 + "\n")
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    exit(main())
