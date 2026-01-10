import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.ai_service import AINotificationService

def test_ai():
    print("--- Testing AI Notification Service ---")
    
    # Initialize without key -> triggers mock/safe mode in our boilerplate
    service = AINotificationService(api_key="sk-fake-key-for-testing") 
    
    # But wait, our boilerplate checks `if not self.client` or throws error if key is invalid.
    # To test nicely without a real key, we should handle the error gracefully or expect failure.
    # However, 'sk-fake...' will likely cause an auth error if we actually hit OpenAI.
    # If the user has an env var set, it will use that.
    
    print("\n1. Generating Content...")
    context = "Employee appreciation lunch this Friday at 12 PM in the cafeteria. Pizza will be served."
    try:
        content = service.generate_notification_content(context)
        print("Result:", content)
    except Exception as e:
        print("Generation failed (Expected if no valid key):", e)

    print("\n2. Classifying Content...")
    try:
        classification = service.classify_notification(
            title="Urgent: Open Enrollment Ends Tomorrow",
            body="Please submit your elections by 5 PM EST."
        )
        print("Result:", classification)
    except Exception as e:
        print("Classification failed (Expected if no valid key):", e)

if __name__ == "__main__":
    test_ai()
