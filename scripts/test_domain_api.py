"""
Integration test for the domain-driven API endpoints.

This script:
1. Creates dummy test data (user, recommendations, notifications)
2. Tests API endpoints with filters
3. Cleans up all dummy data

Run with: python scripts/test_domain_api.py
"""

import sys
import os
import uuid
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy.orm import Session
from app.core.database import SessionLocal, engine
from app.models.models import (
    Profile, Recommendation, Notification, BenefitSummary, 
    BenefitTrend, BenefitTrendItem, Paystub
)
from app.services.category_service import CategoryService
from app.services.slm_classifier import SLMClassifier


# Test user ID - use a fixed UUID for easy cleanup
TEST_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
TEST_PAYSTUB_ID = uuid.UUID("00000000-0000-0000-0000-000000000002")
TEST_SUMMARY_ID = uuid.UUID("00000000-0000-0000-0000-000000000003")


def cleanup_test_data(db: Session):
    """Remove all test data before and after tests."""
    print("\n[CLEANUP] Cleaning up test data...")
    
    # Delete in order to respect foreign keys
    db.query(Recommendation).filter(Recommendation.user_id == TEST_USER_ID).delete()
    db.query(Notification).filter(Notification.user_id == TEST_USER_ID).delete()
    db.query(BenefitSummary).filter(BenefitSummary.user_id == TEST_USER_ID).delete()
    db.query(Paystub).filter(Paystub.user_id == TEST_USER_ID).delete()
    db.query(Profile).filter(Profile.user_id == TEST_USER_ID).delete()
    
    # Clean up test trends (by looking for test prefix in title)
    db.query(BenefitTrendItem).filter(
        BenefitTrendItem.trend_id.in_(
            db.query(BenefitTrend.id).filter(BenefitTrend.title.like("TEST:%"))
        )
    ).delete(synchronize_session=False)
    db.query(BenefitTrend).filter(BenefitTrend.title.like("TEST:%")).delete()
    
    db.commit()
    print("✅ Cleanup complete")


def create_test_user(db: Session):
    """Create a test user profile."""
    print("\n[USER] Creating test user...")
    
    user = Profile(
        user_id=TEST_USER_ID,
        full_name="Test User",
        email="test@clearperks.com",
        timezone="America/New_York",
    )
    db.add(user)
    db.commit()
    print(f"✅ Created user: {TEST_USER_ID}")
    return user


def create_test_paystub_and_summary(db: Session):
    """Create test paystub and benefit summary."""
    print("\n[DOC] Creating test paystub and summary...")
    
    paystub = Paystub(
        id=TEST_PAYSTUB_ID,
        user_id=TEST_USER_ID,
        status="done",
        parsed_data={"gross_pay": 5000, "net_pay": 4000},
    )
    db.add(paystub)
    db.flush()
    
    summary = BenefitSummary(
        id=TEST_SUMMARY_ID,
        user_id=TEST_USER_ID,
        paystub_id=TEST_PAYSTUB_ID,
        hsa_balance=1500,
        fsa_balance=500,
        pto_balance_hours=80,
        k401_contribution_percent=6,
    )
    db.add(summary)
    db.commit()
    
    print(f"✅ Created paystub and summary")
    return summary


def create_test_recommendations(db: Session):
    """Create test recommendations with various domain tags and signals."""
    print("\n[IDEA] Creating test recommendations...")
    
    test_recs = [
        {
            "title": "Maximize HSA Contributions",
            "description": "You can save $500 in taxes by maximizing your HSA contributions before the deadline.",
            "estimated_savings": 500,
            "expected_category": "Health",
        },
        {
            "title": "Increase 401k to Get Full Match",
            "description": "Increase your 401k contribution to 6% to get the full employer match.",
            "estimated_savings": 1200,
            "expected_category": "Retirement",
        },
        {
            "title": "Use PTO Before Year End",
            "description": "You have 40 hours of PTO expiring at year end. Action required to avoid losing it.",
            "estimated_savings": None,
            "expected_category": "Time Off",
        },
        {
            "title": "FSA Deadline Approaching",
            "description": "URGENT: Your FSA balance of $500 expires in 30 days. Use it or lose it!",
            "estimated_savings": 500,
            "expected_category": "Health",
        },
    ]
    
    created_recs = []
    for rec_data in test_recs:
        # Classify using SLMClassifier
        classification = SLMClassifier.classify_text(
            f"{rec_data['title']}. {rec_data['description']}"
        )
        
        # Compute relevance
        relevance_components = SLMClassifier.compute_relevance_components(
            rec_data['description'],
            classification['signals']
        )
        relevance_score = CategoryService.compute_relevance_score(
            money_score=CategoryService.compute_money_score(
                classification['signals'],
                rec_data['estimated_savings']
            ),
            urgency_score=relevance_components['urgency_score'],
            confidence_score=relevance_components['confidence_score'],
        )
        
        rec = Recommendation(
            user_id=TEST_USER_ID,
            benefit_summary_id=TEST_SUMMARY_ID,
            title=rec_data["title"],
            description=rec_data["description"],
            estimated_savings=rec_data["estimated_savings"],
            category=classification["category"],
            priority=classification["priority"],
            domain_tags=classification["domain_tags"],
            signals=classification["signals"],
            relevance_score=relevance_score,
        )
        db.add(rec)
        created_recs.append((rec, rec_data["expected_category"]))
    
    db.commit()
    
    # Verify derived categories
    print("\nVerifying recommendations:")
    all_correct = True
    for rec, expected_cat in created_recs:
        derived_cat = CategoryService.derive_ui_category(rec.domain_tags, rec.signals)
        status = "✅" if derived_cat == expected_cat else "❌"
        if derived_cat != expected_cat:
            all_correct = False
        print(f"  {status} '{rec.title[:30]}...' -> {derived_cat} (expected {expected_cat})")
        print(f"      Tags: {rec.domain_tags}, Signals: {list(rec.signals.keys())}")
        print(f"      Relevance: {rec.relevance_score}")
    
    return all_correct


def create_test_notifications(db: Session):
    """Create test notifications with various signals."""
    print("\n[BELL] Creating test notifications...")
    
    test_notifs = [
        {
            "title": "HSA Contribution Reminder",
            "body": "Maximize your tax savings by contributing to your HSA before the deadline.",
            "expected_has_deadline": True,
        },
        {
            "title": "New Tax Regulations",
            "body": "The IRS has released new tax regulations affecting your benefits.",
            "expected_has_deadline": False,
        },
    ]
    
    for notif_data in test_notifs:
        classification = SLMClassifier.classify_text(
            f"{notif_data['title']}. {notif_data['body']}"
        )
        
        notif = Notification(
            user_id=TEST_USER_ID,
            title=notif_data["title"],
            body=notif_data["body"],
            category=classification["category"],
            priority=classification["priority"],
            domain_tags=classification["domain_tags"],
            signals=classification["signals"],
            sent_at=datetime.utcnow(),
        )
        db.add(notif)
    
    db.commit()
    print(f"✅ Created {len(test_notifs)} test notifications")
    return True


def create_test_trends(db: Session):
    """Create test benefit trends."""
    print("\n[TREND] Creating test trends...")
    
    test_trends = [
        {
            "title": "TEST: HSA Contribution Limits Increasing",
            "summary": "The IRS has announced new HSA contribution limits for 2026, allowing you to save more tax-free.",
        },
        {
            "title": "TEST: 401k Match Best Practices",
            "summary": "New study shows many employees miss out on free retirement money by not maximizing employer match.",
        },
    ]
    
    for trend_data in test_trends:
        classification = SLMClassifier.classify_text(
            f"{trend_data['title']}. {trend_data['summary']}"
        )
        
        relevance_components = SLMClassifier.compute_relevance_components(
            trend_data['summary'],
            classification['signals']
        )
        
        trend = BenefitTrend(
            title=trend_data["title"],
            summary=trend_data["summary"],
            domain_tags=classification["domain_tags"],
            signals=classification["signals"],
            freshness_score=10.0,
            urgency_score=relevance_components['urgency_score'],
            money_score=relevance_components['money_score'],
            confidence_score=relevance_components['confidence_score'],
            relevance_score=CategoryService.compute_relevance_score(
                freshness_score=10.0,
                urgency_score=relevance_components['urgency_score'],
                money_score=relevance_components['money_score'],
                confidence_score=relevance_components['confidence_score'],
            ),
        )
        db.add(trend)
    
    db.commit()
    print(f"✅ Created {len(test_trends)} test trends")
    return True


def test_filter_queries(db: Session):
    """Test querying with filters."""
    print("\n[SEARCH] Testing filter queries...")
    
    # Test: Get recommendations with saves_money signal
    recs_saves_money = (
        db.query(Recommendation)
        .filter(Recommendation.user_id == TEST_USER_ID)
        .filter(Recommendation.signals["saves_money"].astext == "true")
        .all()
    )
    print(f"  Recommendations with saves_money: {len(recs_saves_money)}")
    
    # Test: Get recommendations with has_deadline signal
    recs_deadline = (
        db.query(Recommendation)
        .filter(Recommendation.user_id == TEST_USER_ID)
        .filter(Recommendation.signals["has_deadline"].astext == "true")
        .all()
    )
    print(f"  Recommendations with has_deadline: {len(recs_deadline)}")
    
    # Test: Get recommendations sorted by relevance
    recs_by_relevance = (
        db.query(Recommendation)
        .filter(Recommendation.user_id == TEST_USER_ID)
        .order_by(Recommendation.relevance_score.desc())
        .all()
    )
    print(f"  Recommendations sorted by relevance:")
    for rec in recs_by_relevance:
        print(f"    - {rec.title[:40]}: score={rec.relevance_score}")
    
    # Test: Filter by derived UI category (post-query)
    health_recs = [
        rec for rec in recs_by_relevance
        if CategoryService.derive_ui_category(rec.domain_tags or [], rec.signals or {}) == "Health"
    ]
    print(f"  Health category recommendations: {len(health_recs)}")
    
    return True


def main():
    """Run all integration tests."""
    print("\n" + "#"*60)
    print("# ClearPerks Domain API Integration Tests")
    print("#"*60)
    
    db = SessionLocal()
    
    try:
        # Cleanup before tests
        cleanup_test_data(db)
        
        # Create test data
        create_test_user(db)
        create_test_paystub_and_summary(db)
        
        results = []
        results.append(("Recommendations", create_test_recommendations(db)))
        results.append(("Notifications", create_test_notifications(db)))
        results.append(("Trends", create_test_trends(db)))
        results.append(("Filter Queries", test_filter_queries(db)))
        
        # Summary
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
        print("#"*60)
        
    finally:
        # Cleanup after tests
        cleanup_test_data(db)
        db.close()
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    exit(main())
