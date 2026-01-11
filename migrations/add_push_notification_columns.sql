"""
Database migration script for adding push notification columns.

This script adds the necessary columns to support push notifications:
- notifications.push_sent: Track if push was successfully sent
- notifications.push_error: Store any push delivery errors
- notifications.should_push: Flag to control push sending per notification

Run this after deploying the new code but before enabling push notifications.
"""

-- Add push notification tracking columns to notifications table
ALTER TABLE notifications 
    ADD COLUMN IF NOT EXISTS push_sent BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS push_error TEXT,
    ADD COLUMN IF NOT EXISTS should_push BOOLEAN DEFAULT TRUE;

-- Add index for performance on push status queries
CREATE INDEX IF NOT EXISTS idx_notifications_push_status 
    ON notifications(push_sent, should_push) 
    WHERE push_sent = FALSE;

-- Add unique constraint to device_tokens to prevent duplicates
ALTER TABLE device_tokens 
    ADD CONSTRAINT IF NOT EXISTS device_tokens_user_token_unique 
    UNIQUE (user_id, token);

-- Add platform validation constraint
ALTER TABLE device_tokens 
    DROP CONSTRAINT IF EXISTS device_tokens_platform_check;

ALTER TABLE device_tokens 
    ADD CONSTRAINT device_tokens_platform_check 
    CHECK (platform IN ('ios', 'android', 'web') OR platform IS NULL);

-- Add index for faster device token lookups
CREATE INDEX IF NOT EXISTS idx_device_tokens_user 
    ON device_tokens(user_id);

COMMENT ON COLUMN notifications.push_sent IS 'Whether push notification was successfully sent via FCM';
COMMENT ON COLUMN notifications.push_error IS 'Error message if push notification failed';
COMMENT ON COLUMN notifications.should_push IS 'Whether this notification should trigger a push (can be disabled per notification)';
