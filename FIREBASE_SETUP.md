# Firebase Cloud Messaging Setup Guide

This guide walks you through setting up Firebase Cloud Messaging (FCM) for the ClearPerks backend to enable push notifications.

## Prerequisites

- Google account
- ClearPerks backend codebase

## Step 1: Create Firebase Project

1. **Navigate to Firebase Console**
   - Open your browser to: https://console.firebase.google.com/
   - The browser has already been opened for you

2. **Create New Project**
   - Click **"Add project"** or **"Create a project"**
   - Enter project name: `ClearPerks` (or any name you prefer)
   - Click **"Continue"**

3. **Disable Google Analytics** (Optional)
   - Toggle off "Enable Google Analytics for this project"
   - Analytics is not required for push notifications
   - Click **"Create project"**

4. **Wait for Project Creation**
   - Firebase will set up your project (takes ~30 seconds)
   - Click **"Continue"** when ready

## Step 2: Enable Cloud Messaging API

1. **Navigate to Project Settings**
   - Click the ⚙️ gear icon next to "Project Overview"
   - Select **"Project settings"**

2. **Go to Cloud Messaging Tab**
   - Click on the **"Cloud Messaging"** tab
   - Firebase Cloud Messaging API should be enabled by default
   - If not, click **"Enable Cloud Messaging API"**

## Step 3: Generate Service Account Credentials

1. **Navigate to Service Accounts**
   - In Project Settings, click the **"Service accounts"** tab

2. **Generate Private Key**
   - Click **"Generate new private key"** button
   - A dialog will appear warning that this key should be kept secure
   - Click **"Generate key"**

3. **Download JSON File**
   - A JSON file will automatically download
   - File name will be like: `clearperks-firebase-adminsdk-xxxxx-xxxxxxxxxx.json`
   - **IMPORTANT:** Keep this file secure - it contains sensitive credentials

4. **Rename and Move File**
   - Rename the downloaded file to: `firebase-credentials.json`
   - Move it to your backend project root directory:
     ```
     d:\2025\ClearPerks-backend\firebase-credentials.json
     ```

## Step 4: Configure Environment Variables

1. **Open `.env` file**
   - Located at: `d:\2025\ClearPerks-backend\.env`

2. **Add Firebase Configuration**
   - Add these lines to your `.env` file:
   ```bash
   # Firebase Cloud Messaging Configuration
   FIREBASE_CREDENTIALS_PATH=./firebase-credentials.json
   FIREBASE_ENABLED=true
   ```

3. **Save the file**

## Step 5: Verify Setup

Run the test script to verify Firebase connection:

```powershell
cd d:\2025\ClearPerks-backend
python scripts\test_fcm_integration.py
```

Expected output:
```
✓ Firebase initialized successfully
✓ FCM is enabled and ready
```

## Step 6: Get FCM Server Key (For Mobile Apps)

Your mobile app team will need the FCM server key to integrate push notifications.

1. **Navigate to Cloud Messaging Settings**
   - In Firebase Console, go to **Project Settings** → **Cloud Messaging**

2. **Find Server Key**
   - Under **"Project credentials"** section
   - Look for **"Server key"** field
   - Click the copy icon to copy the key

3. **Share with Mobile Team**
   - Provide this key to your iOS/Android developers
   - They'll need it to configure Firebase in the mobile app

## Step 7: Add Firebase to Mobile Apps

### For iOS:
1. In Firebase Console, click **"Add app"** → iOS icon
2. Register your app with Bundle ID
3. Download `GoogleService-Info.plist`
4. Add to Xcode project
5. Install Firebase SDK via CocoaPods or SPM

### For Android:
1. In Firebase Console, click **"Add app"** → Android icon
2. Register your app with package name
3. Download `google-services.json`
4. Add to `app/` directory in Android project
5. Install Firebase SDK via Gradle

## Security Best Practices

1. **Never Commit Credentials**
   - The `firebase-credentials.json` file is already in `.gitignore`
   - Never commit this file to version control
   - Never share this file publicly

2. **Rotate Keys Periodically**
   - Generate a new service account key annually
   - Delete old keys from Firebase Console after rotation

3. **Production Deployment**
   - For production, use environment variables or secret managers
   - Examples: Kubernetes Secrets, AWS Secrets Manager, Azure Key Vault
   - Don't store credentials file directly on production servers

4. **Limit Permissions**
   - Use the generated service account only for FCM
   - Don't use your personal Google account credentials

## Troubleshooting

### Error: "Firebase credentials file not found"
- Verify file exists at: `d:\2025\ClearPerks-backend\firebase-credentials.json`
- Check that `FIREBASE_CREDENTIALS_PATH` in `.env` is correct

### Error: "Permission denied on firebase-credentials.json"
- Make sure the file has read permissions
- On Windows, right-click → Properties → Security → check read access

### Error: "Invalid credentials"
- Re-download the service account key from Firebase Console
- Ensure you downloaded the correct project's credentials
- Verify the JSON file is not corrupted

### Push Notifications Not Working
1. Check Firebase Console for error messages
2. Verify mobile app has registered device token
3. Check backend logs for push errors
4. Ensure `FIREBASE_ENABLED=true` in `.env`

## Next Steps

1. ✅ Firebase project created
2. ✅ Service account credentials downloaded
3. ✅ Backend configured with credentials
4. 🔄 **Next:** Test push notification integration
5. 🔄 **Next:** Update mobile apps to register device tokens

## Support

For issues specific to:
- **Firebase Console:** https://firebase.google.com/support
- **Backend Integration:** Check backend logs and test scripts
- **Mobile Integration:** Refer to Firebase iOS/Android documentation

---

**Status:** Once you've completed steps 1-4, the backend is ready to send push notifications!
