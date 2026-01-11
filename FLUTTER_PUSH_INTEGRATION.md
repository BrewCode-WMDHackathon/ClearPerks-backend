# ClearPerks Flutter Push Notification Integration Guide

## Overview

This document provides complete instructions for integrating Firebase Cloud Messaging (FCM) push notifications into the ClearPerks Flutter mobile app. The backend is already configured and ready to send push notifications.

---

## Functional Requirements

### What This Integration Achieves

1. **Real-time Notifications**: Users receive instant push notifications for:
   - Benefits updates and reminders
   - FSA/HSA deadline alerts
   - PTO balance notifications
   - Custom admin announcements
   - Government benefits updates

2. **Hybrid Delivery**: 
   - **Push**: Instant delivery when app is in background/closed
   - **Pull**: Fetch notification history when user opens notification screen

3. **User Experience**:
   - Notifications appear in device notification tray
   - Tapping notification opens the app to relevant content
   - Badge count shows unread notifications
   - Silent push for data sync (optional)

### User Stories

| Story | Description |
|-------|-------------|
| US-1 | As a user, I want to receive push notifications when my FSA deadline is approaching |
| US-2 | As a user, I want to tap a notification and be taken to the relevant screen |
| US-3 | As a user, I want to control which notifications I receive |
| US-4 | As a user, I want to see a notification badge showing unread count |

---

## Technical Architecture

### System Flow

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   ClearPerks    │     │    Firebase     │     │   ClearPerks    │
│    Backend      │────▶│   Cloud Msg     │────▶│   Flutter App   │
│   (FastAPI)     │     │     (FCM)       │     │                 │
└─────────────────┘     └─────────────────┘     └─────────────────┘
        │                                               │
        │  1. Create notification                       │
        │  2. Send to FCM with device tokens            │
        │  3. FCM delivers to device                    │
        │                                               │
        ▼                                               ▼
┌─────────────────┐                         ┌─────────────────┐
│   PostgreSQL    │                         │  Local Storage  │
│   (Supabase)    │                         │  (Hive/SQLite)  │
└─────────────────┘                         └─────────────────┘
```

### Backend API Endpoints (Already Implemented)

| Endpoint | Method | Description | Auth |
|----------|--------|-------------|------|
| `/api/v1/devices/register` | POST | Register FCM device token | Required |
| `/api/v1/devices/{token}` | DELETE | Unregister token (logout) | Required |
| `/api/v1/devices` | GET | List user's registered devices | Required |
| `/api/v1/notifications` | GET | Fetch all notifications | Required |
| `/api/v1/notifications/{id}/read` | PATCH | Mark notification as read | Required |

### Firebase Project Details

- **Project Name**: ClearPerks
- **Project ID**: `clearperks-bb101`
- **Console URL**: https://console.firebase.google.com/project/clearperks-bb101

---

## Implementation Steps

### Step 1: Add Firebase to Flutter Project

#### 1.1 Install FlutterFire CLI
```bash
dart pub global activate flutterfire_cli
```

#### 1.2 Configure Firebase
```bash
flutterfire configure --project=clearperks-bb101
```

This will:
- Create `firebase_options.dart` in your lib folder
- Download and configure `google-services.json` (Android)
- Download and configure `GoogleService-Info.plist` (iOS)

#### 1.3 Add Dependencies to `pubspec.yaml`
```yaml
dependencies:
  firebase_core: ^3.10.0
  firebase_messaging: ^15.2.0
  flutter_local_notifications: ^18.0.1
```

Run:
```bash
flutter pub get
```

---

### Step 2: Initialize Firebase

#### 2.1 Update `main.dart`

```dart
import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'firebase_options.dart';
import 'services/push_notification_service.dart';

// Background message handler (must be top-level function)
@pragma('vm:entry-point')
Future<void> _firebaseMessagingBackgroundHandler(RemoteMessage message) async {
  await Firebase.initializeApp(options: DefaultFirebaseOptions.currentPlatform);
  print('Background message: ${message.notification?.title}');
  // Handle background message (e.g., update local cache)
}

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  
  // Initialize Firebase
  await Firebase.initializeApp(
    options: DefaultFirebaseOptions.currentPlatform,
  );
  
  // Set background message handler
  FirebaseMessaging.onBackgroundMessage(_firebaseMessagingBackgroundHandler);
  
  // Initialize push notification service
  await PushNotificationService.instance.initialize();
  
  runApp(const MyApp());
}
```

---

### Step 3: Create Push Notification Service

#### 3.1 Create `lib/services/push_notification_service.dart`

```dart
import 'dart:convert';
import 'dart:io';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';
import 'package:http/http.dart' as http;

/// Service for handling push notifications
class PushNotificationService {
  static final PushNotificationService instance = PushNotificationService._();
  PushNotificationService._();

  final FirebaseMessaging _fcm = FirebaseMessaging.instance;
  final FlutterLocalNotificationsPlugin _localNotifications =
      FlutterLocalNotificationsPlugin();

  String? _fcmToken;
  String? get fcmToken => _fcmToken;

  // Callback for when user taps notification
  Function(String? notificationId)? onNotificationTapped;

  /// Initialize push notification service
  Future<void> initialize() async {
    // Request permission
    await _requestPermission();

    // Initialize local notifications (for foreground)
    await _initLocalNotifications();

    // Get FCM token
    await _getToken();

    // Listen for token refresh
    _fcm.onTokenRefresh.listen(_onTokenRefresh);

    // Handle foreground messages
    FirebaseMessaging.onMessage.listen(_handleForegroundMessage);

    // Handle notification tap (app in background)
    FirebaseMessaging.onMessageOpenedApp.listen(_handleNotificationTap);

    // Check if app was opened from notification (app terminated)
    final initialMessage = await _fcm.getInitialMessage();
    if (initialMessage != null) {
      _handleNotificationTap(initialMessage);
    }
  }

  /// Request notification permission
  Future<void> _requestPermission() async {
    final settings = await _fcm.requestPermission(
      alert: true,
      badge: true,
      sound: true,
      provisional: false,
    );

    print('Notification permission: ${settings.authorizationStatus}');
  }

  /// Initialize local notifications for foreground display
  Future<void> _initLocalNotifications() async {
    const androidSettings = AndroidInitializationSettings('@mipmap/ic_launcher');
    const iosSettings = DarwinInitializationSettings(
      requestAlertPermission: false,
      requestBadgePermission: false,
      requestSoundPermission: false,
    );

    await _localNotifications.initialize(
      const InitializationSettings(
        android: androidSettings,
        iOS: iosSettings,
      ),
      onDidReceiveNotificationResponse: (response) {
        final payload = response.payload;
        if (payload != null) {
          final data = jsonDecode(payload);
          onNotificationTapped?.call(data['notification_id']);
        }
      },
    );

    // Create notification channel for Android
    if (Platform.isAndroid) {
      await _localNotifications
          .resolvePlatformSpecificImplementation<
              AndroidFlutterLocalNotificationsPlugin>()
          ?.createNotificationChannel(
            const AndroidNotificationChannel(
              'clearperks_notifications',
              'ClearPerks Notifications',
              description: 'Notifications from ClearPerks app',
              importance: Importance.high,
            ),
          );
    }
  }

  /// Get FCM device token
  Future<String?> _getToken() async {
    try {
      _fcmToken = await _fcm.getToken();
      print('FCM Token: $_fcmToken');
      return _fcmToken;
    } catch (e) {
      print('Error getting FCM token: $e');
      return null;
    }
  }

  /// Handle token refresh
  void _onTokenRefresh(String newToken) {
    print('FCM Token refreshed: $newToken');
    _fcmToken = newToken;
    // Re-register with backend
    // This will be called by AuthService after login
  }

  /// Handle foreground messages
  void _handleForegroundMessage(RemoteMessage message) {
    print('Foreground message: ${message.notification?.title}');

    final notification = message.notification;
    if (notification != null) {
      // Show local notification
      _localNotifications.show(
        message.hashCode,
        notification.title,
        notification.body,
        NotificationDetails(
          android: AndroidNotificationDetails(
            'clearperks_notifications',
            'ClearPerks Notifications',
            importance: Importance.high,
            priority: Priority.high,
            icon: '@mipmap/ic_launcher',
          ),
          iOS: const DarwinNotificationDetails(
            presentAlert: true,
            presentBadge: true,
            presentSound: true,
          ),
        ),
        payload: jsonEncode(message.data),
      );
    }
  }

  /// Handle notification tap
  void _handleNotificationTap(RemoteMessage message) {
    print('Notification tapped: ${message.data}');
    final notificationId = message.data['notification_id'];
    onNotificationTapped?.call(notificationId);
  }

  /// Register device token with backend
  Future<bool> registerWithBackend({
    required String baseUrl,
    required String authToken,
  }) async {
    if (_fcmToken == null) {
      await _getToken();
    }

    if (_fcmToken == null) {
      print('No FCM token available');
      return false;
    }

    try {
      final response = await http.post(
        Uri.parse('$baseUrl/api/v1/devices/register'),
        headers: {
          'Authorization': 'Bearer $authToken',
          'Content-Type': 'application/json',
        },
        body: jsonEncode({
          'token': _fcmToken,
          'platform': Platform.isIOS ? 'ios' : 'android',
        }),
      );

      if (response.statusCode == 201 || response.statusCode == 200) {
        print('Device token registered successfully');
        return true;
      } else {
        print('Failed to register device token: ${response.body}');
        return false;
      }
    } catch (e) {
      print('Error registering device token: $e');
      return false;
    }
  }

  /// Unregister device token from backend (call on logout)
  Future<bool> unregisterFromBackend({
    required String baseUrl,
    required String authToken,
  }) async {
    if (_fcmToken == null) return true;

    try {
      final response = await http.delete(
        Uri.parse('$baseUrl/api/v1/devices/$_fcmToken'),
        headers: {
          'Authorization': 'Bearer $authToken',
        },
      );

      return response.statusCode == 204;
    } catch (e) {
      print('Error unregistering device token: $e');
      return false;
    }
  }
}
```

---

### Step 4: Integrate with Authentication

#### 4.1 Register Token After Login

```dart
// In your login/auth service, after successful login:
Future<void> onLoginSuccess(String authToken) async {
  // Register device for push notifications
  await PushNotificationService.instance.registerWithBackend(
    baseUrl: 'https://your-api-url.com',
    authToken: authToken,
  );
}
```

#### 4.2 Unregister Token on Logout

```dart
// In your logout function:
Future<void> logout() async {
  // Unregister device token
  await PushNotificationService.instance.unregisterFromBackend(
    baseUrl: 'https://your-api-url.com',
    authToken: currentAuthToken,
  );
  
  // Clear auth state
  // Navigate to login screen
}
```

---

### Step 5: Handle Notification Navigation

#### 5.1 Set Up Navigation Handler

```dart
// In your main app widget or navigation service:
void initNotificationHandlers() {
  PushNotificationService.instance.onNotificationTapped = (notificationId) {
    if (notificationId != null) {
      // Navigate to notification detail or relevant screen
      Navigator.of(context).pushNamed(
        '/notification-detail',
        arguments: notificationId,
      );
    } else {
      // Navigate to notifications list
      Navigator.of(context).pushNamed('/notifications');
    }
  };
}
```

---

### Step 6: Platform-Specific Configuration

#### 6.1 Android Configuration

**android/app/build.gradle**:
```gradle
android {
    defaultConfig {
        minSdkVersion 21  // Required for FCM
    }
}
```

**android/app/src/main/AndroidManifest.xml**:
```xml
<manifest>
    <!-- Add these permissions -->
    <uses-permission android:name="android.permission.INTERNET"/>
    <uses-permission android:name="android.permission.POST_NOTIFICATIONS"/>
    
    <application>
        <!-- FCM Default Notification Channel -->
        <meta-data
            android:name="com.google.firebase.messaging.default_notification_channel_id"
            android:value="clearperks_notifications" />
            
        <!-- FCM Default Notification Icon -->
        <meta-data
            android:name="com.google.firebase.messaging.default_notification_icon"
            android:resource="@mipmap/ic_launcher" />
            
        <!-- FCM Default Notification Color -->
        <meta-data
            android:name="com.google.firebase.messaging.default_notification_color"
            android:resource="@color/colorPrimary" />
    </application>
</manifest>
```

#### 6.2 iOS Configuration

**ios/Runner/Info.plist**:
```xml
<dict>
    <!-- Add background modes -->
    <key>UIBackgroundModes</key>
    <array>
        <string>fetch</string>
        <string>remote-notification</string>
    </array>
    
    <!-- Firebase auto-init -->
    <key>FirebaseAppDelegateProxyEnabled</key>
    <false/>
</dict>
```

**ios/Runner/AppDelegate.swift**:
```swift
import UIKit
import Flutter
import FirebaseCore
import FirebaseMessaging

@main
@objc class AppDelegate: FlutterAppDelegate {
  override func application(
    _ application: UIApplication,
    didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?
  ) -> Bool {
    FirebaseApp.configure()
    
    // Request notification authorization
    UNUserNotificationCenter.current().delegate = self
    
    let authOptions: UNAuthorizationOptions = [.alert, .badge, .sound]
    UNUserNotificationCenter.current().requestAuthorization(
      options: authOptions,
      completionHandler: { _, _ in }
    )
    
    application.registerForRemoteNotifications()
    
    GeneratedPluginRegistrant.register(with: self)
    return super.application(application, didFinishLaunchingWithOptions: launchOptions)
  }
  
  override func application(
    _ application: UIApplication,
    didRegisterForRemoteNotificationsWithDeviceToken deviceToken: Data
  ) {
    Messaging.messaging().apnsToken = deviceToken
  }
}
```

---

## Testing Checklist

### Local Testing

- [ ] FCM token is generated on app start
- [ ] Token is registered with backend on login
- [ ] Foreground notifications display correctly
- [ ] Background notifications appear in system tray
- [ ] Tapping notification opens correct screen
- [ ] Token is unregistered on logout
- [ ] Token refresh is handled correctly

### Backend Testing

```bash
# 1. Register a device token (use real token from app)
curl -X POST https://your-api.com/api/v1/devices/register \
  -H "Authorization: Bearer YOUR_JWT" \
  -H "Content-Type: application/json" \
  -d '{"token": "FCM_TOKEN", "platform": "android"}'

# 2. Send a test notification
curl -X POST https://your-api.com/api/v1/admin/notifications/send \
  -H "Authorization: Bearer ADMIN_JWT" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "USER_UUID",
    "title": "Test Notification",
    "body": "This is a test push notification",
    "category": "manual",
    "priority": "high"
  }'

# 3. Check notification was received on device
```

---

## Notification Payload Format

### Push Notification Structure

```json
{
  "notification": {
    "title": "FSA Deadline Reminder",
    "body": "Your FSA funds expire in 30 days. You have $500 remaining."
  },
  "data": {
    "notification_id": "uuid-here",
    "category": "fsa",
    "priority": "high"
  }
}
```

### Handling Different Categories

```dart
void handleNotificationByCategory(String? category, String? notificationId) {
  switch (category) {
    case 'fsa':
      Navigator.pushNamed(context, '/benefits/fsa');
      break;
    case 'pto':
      Navigator.pushNamed(context, '/benefits/pto');
      break;
    case 'news':
      Navigator.pushNamed(context, '/news');
      break;
    default:
      Navigator.pushNamed(context, '/notifications');
  }
}
```

---

## Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| No FCM token | Check Firebase initialization, ensure google-services.json is correct |
| Token not registered | Verify backend URL and auth token are correct |
| No push received | Check Firebase Console for delivery status, verify token is registered |
| iOS not working | Ensure APNs certificate is uploaded to Firebase |
| Background handler not called | Ensure handler is top-level function with @pragma annotation |

### Debug Mode

```dart
// Enable FCM debug logging
FirebaseMessaging.instance.setDeliveryMetricsExportToBigQuery(true);

// Print all incoming messages
FirebaseMessaging.onMessage.listen((message) {
  print('=== FCM MESSAGE ===');
  print('Title: ${message.notification?.title}');
  print('Body: ${message.notification?.body}');
  print('Data: ${message.data}');
});
```

---

## Security Considerations

1. **Token Storage**: FCM tokens are not sensitive, but don't expose them publicly
2. **Backend Validation**: Backend validates user owns the token before registering
3. **Logout Cleanup**: Always unregister token on logout to prevent notifications to wrong user
4. **Sensitive Data**: Never include sensitive data in push payload - fetch via API instead

---

## Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `lib/main.dart` | Modify | Add Firebase initialization |
| `lib/services/push_notification_service.dart` | Create | Push notification handling |
| `lib/firebase_options.dart` | Auto-generated | Firebase configuration |
| `android/app/google-services.json` | Auto-generated | Android Firebase config |
| `ios/Runner/GoogleService-Info.plist` | Auto-generated | iOS Firebase config |
| `android/app/src/main/AndroidManifest.xml` | Modify | Add permissions and meta-data |
| `ios/Runner/Info.plist` | Modify | Add background modes |
| `ios/Runner/AppDelegate.swift` | Modify | Configure Firebase and APNs |
| `pubspec.yaml` | Modify | Add dependencies |

---

## Summary

This integration provides:
- ✅ Real-time push notifications via FCM
- ✅ Proper handling of foreground, background, and terminated states
- ✅ Navigation to relevant content when notification is tapped
- ✅ Token lifecycle management (register on login, unregister on logout)
- ✅ Both Android and iOS support

The backend is already fully configured. Follow these steps to complete the Flutter integration.
