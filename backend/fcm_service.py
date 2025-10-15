# Firebase Cloud Messaging Backend Integration
# Handles FCM token storage and sending push notifications

import os
import firebase_admin
from firebase_admin import credentials, messaging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone

# Create router
fcm_router = APIRouter(prefix="/fcm", tags=["fcm"])

# Initialize Firebase Admin SDK (will be initialized from server.py)
# This is just a placeholder - actual initialization happens in server.py

class FCMTokenRequest(BaseModel):
    user_id: str
    fcm_token: str
    device_type: str = "web"

class FCMNotificationRequest(BaseModel):
    user_id: str
    title: str
    body: str
    data: Optional[dict] = None
    notification_type: str = "general"

# Store FCM tokens in MongoDB (imported from server.py)
async def save_fcm_token(db, user_id: str, fcm_token: str, device_type: str):
    """Save FCM token to user document"""
    try:
        await db.users.update_one(
            {"id": user_id},
            {
                "$set": {
                    "fcm_token": fcm_token,
                    "device_type": device_type,
                    "fcm_updated_at": datetime.now(timezone.utc)
                }
            }
        )
        print(f"✅ FCM token saved for user: {user_id}")
        return True
    except Exception as e:
        print(f"❌ Error saving FCM token: {e}")
        return False

async def get_user_fcm_token(db, user_id: str):
    """Get FCM token for a user"""
    try:
        user = await db.users.find_one({"id": user_id})
        if user and "fcm_token" in user:
            return user["fcm_token"]
        return None
    except Exception as e:
        print(f"❌ Error getting FCM token: {e}")
        return None

async def send_fcm_notification(fcm_token: str, title: str, body: str, data: dict = None):
    """Send FCM notification to a specific device"""
    try:
        # Create message
        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body
            ),
            data=data or {},
            token=fcm_token,
            webpush=messaging.WebpushConfig(
                notification=messaging.WebpushNotification(
                    title=title,
                    body=body,
                    icon="/favicon.ico",
                    badge="/favicon.ico",
                    require_interaction=data.get("type") in ["video_call", "emergency"] if data else False
                ),
                fcm_options=messaging.WebpushFCMOptions(
                    link="/"
                )
            )
        )
        
        # Send message
        response = messaging.send(message)
        print(f"✅ FCM notification sent successfully: {response}")
        return True
    except Exception as e:
        print(f"❌ Error sending FCM notification: {e}")
        return False

async def send_notification_to_user(db, user_id: str, title: str, body: str, data: dict = None):
    """Send notification to a specific user by user_id"""
    try:
        fcm_token = await get_user_fcm_token(db, user_id)
        if fcm_token:
            return await send_fcm_notification(fcm_token, title, body, data)
        else:
            print(f"⚠️ No FCM token found for user: {user_id}")
            return False
    except Exception as e:
        print(f"❌ Error sending notification to user: {e}")
        return False
