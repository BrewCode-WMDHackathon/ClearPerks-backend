"""
Test script for Firebase Cloud Messaging integration.

This script verifies that:
1. Firebase credentials are properly configured
2. FCM client initializes successfully
3. Push notification service is ready

Run this after setting up Firebase credentials.
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.push_notification_service import push_service

def test_fcm_integration():
    """Test Firebase Cloud Messaging integration"""
    print("Testing Firebase Cloud Messaging Integration...\n")
    
    # Check if firebase credentials file exists
    cred_path = os.getenv("FIREBASE_CREDENTIALS_PATH", "./firebase-credentials.json")
    print(f"1. Checking for credentials file at: {cred_path}")
    
    if not os.path.exists(cred_path):
        print(f"   [X] FAILED: Credentials file not found!")
        print(f"   Please download firebase-credentials.json from Firebase Console")
        print(f"   See FIREBASE_SETUP.md for instructions")
        return False
    else:
        print(f"   [OK] Credentials file found")
    
    # Check if FCM is enabled
    print("\n2. Checking FIREBASE_ENABLED environment variable")
    fcm_enabled = os.getenv("FIREBASE_ENABLED", "true").lower() == "true"
    
    if not fcm_enabled:
        print(f"   [!] WARNING: FIREBASE_ENABLED is set to false")
        print(f"   Set FIREBASE_ENABLED=true in .env to enable push notifications")
        return False
    else:
        print(f"   [OK] Firebase is enabled")
    
    # Try to initialize FCM
    print("\n3. Initializing Firebase Cloud Messaging...")
    try:
        result = push_service.initialize_fcm()
        
        if result:
            print(f"   [OK] Firebase initialized successfully!")
        else:
            print(f"   [X] FAILED: Firebase initialization returned False")
            print(f"   Check if firebase-admin is installed: pip install firebase-admin")
            return False
            
    except Exception as e:
        print(f"   [X] FAILED: {str(e)}")
        return False
    
    # Check if push service is ready
    print("\n4. Verifying push service is ready...")
    if push_service.is_enabled():
        print(f"   [OK] Push notification service is ready!")
    else:
        print(f"   [X] FAILED: Push notification service is not ready")
        return False
    
    print("\n" + "="*60)
    print("[SUCCESS] Firebase Cloud Messaging is properly configured")
    print("="*60)
    print("\nNext steps:")
    print("1. Run the backend: uvicorn app.main:app --reload")
    print("2. Register a device token via POST /api/v1/devices/register")
    print("3. Send a test notification via POST /api/v1/admin/notifications/send")
    print("\nFor mobile app integration, see FIREBASE_SETUP.md\n")
    
    return True


if __name__ == "__main__":
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    success = test_fcm_integration()
    sys.exit(0 if success else 1)
