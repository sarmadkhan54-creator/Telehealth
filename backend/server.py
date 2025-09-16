from fastapi import FastAPI, APIRouter, HTTPException, Depends, status, WebSocket, WebSocketDisconnect
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import asyncio
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone, timedelta
import jwt
from passlib.context import CryptContext
import json
from pywebpush import webpush, WebPushException
import base64

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI(title="MedConnect Telehealth API", version="1.0.0")

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Security
SECRET_KEY = "your-secret-key-change-this-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

# VAPID Keys for push notifications (in production, store these securely)
VAPID_PRIVATE_KEY = """-----BEGIN EC PRIVATE KEY-----
MHcCAQEEIKK8I4f3dR4hM+JR3kT9PVZsYr1GG2LBP1FJMDhj9cVDoAoGCCqGSM49
AwEHoUQDQgAE9Gkaw4D3VWM5LHRrC4k8kGy8nJo9L0fP2T5K5aWqMxQ8vF8Vr4bN
2mK3L8V9rJoX5F7gG3YtH8vKlX7N5pQ2cg==
-----END EC PRIVATE KEY-----"""

VAPID_PUBLIC_KEY = "BPRpGsOA91VjOSx0awuJPJBsvJyaPS9Hz9k+SuWlqjMUPLxfFa+GzdpiKvX8Vr4bN2mK3L8V9rJoX5F7gG3YtH8vKlX7N5pQ2cg"

VAPID_CLAIMS = {
    "sub": "mailto:admin@greenstar-health.com"
}

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, user_id: str):
        await websocket.accept()
        self.active_connections[user_id] = websocket
    
    def disconnect(self, user_id: str):
        if user_id in self.active_connections:
            del self.active_connections[user_id]
    
    async def send_personal_message(self, message: dict, user_id: str):
        if user_id in self.active_connections:
            try:
                await self.active_connections[user_id].send_text(json.dumps(message))
            except:
                self.disconnect(user_id)

# WebSocket connection manager for video calls
class VideoCallManager:
    def __init__(self):
        self.active_sessions: Dict[str, Dict[str, WebSocket]] = {}  # session_token -> {user_id: websocket}
    
    async def join_session(self, session_token: str, user_id: str, websocket: WebSocket, user_name: str):
        await websocket.accept()
        
        if session_token not in self.active_sessions:
            self.active_sessions[session_token] = {}
        
        self.active_sessions[session_token][user_id] = websocket
        
        # Notify other users in the session
        for other_user_id, other_ws in self.active_sessions[session_token].items():
            if other_user_id != user_id:
                try:
                    await other_ws.send_text(json.dumps({
                        "type": "user-joined",
                        "userId": user_id,
                        "userName": user_name
                    }))
                except:
                    pass
    
    def leave_session(self, session_token: str, user_id: str):
        if session_token in self.active_sessions and user_id in self.active_sessions[session_token]:
            # Notify other users
            for other_user_id, other_ws in self.active_sessions[session_token].items():
                if other_user_id != user_id:
                    try:
                        asyncio.create_task(other_ws.send_text(json.dumps({
                            "type": "user-left",
                            "userId": user_id
                        })))
                    except:
                        pass
            
            del self.active_sessions[session_token][user_id]
            
            # Remove session if empty
            if not self.active_sessions[session_token]:
                del self.active_sessions[session_token]
    
    async def relay_message(self, session_token: str, from_user_id: str, message: dict):
        if session_token in self.active_sessions:
            target_user_id = message.get('target')
            
            # If target specified, send only to target
            if target_user_id and target_user_id in self.active_sessions[session_token]:
                try:
                    message['from'] = from_user_id
                    await self.active_sessions[session_token][target_user_id].send_text(json.dumps(message))
                except:
                    pass
            else:
                # Broadcast to all other users in session
                for user_id, ws in self.active_sessions[session_token].items():
                    if user_id != from_user_id:
                        try:
                            message['from'] = from_user_id
                            await ws.send_text(json.dumps(message))
                        except:
                            pass

manager = ConnectionManager()
video_call_manager = VideoCallManager()

# Pydantic Models and Constants
class UserRole:
    ADMIN = "admin"
    PROVIDER = "provider" 
    DOCTOR = "doctor"

class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    username: str
    email: EmailStr
    phone: str
    full_name: str
    role: str  # admin, provider, doctor
    district: Optional[str] = None
    specialty: Optional[str] = None  # for doctors
    is_active: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    phone: str
    full_name: str
    role: str
    district: Optional[str] = None
    specialty: Optional[str] = None

class UserLogin(BaseModel):
    username: str
    password: str

class Patient(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    age: int
    gender: str
    vitals: Dict[str, Any] = Field(default_factory=dict)  # blood_pressure, heart_rate, temperature, etc.
    consultation_reason: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class PatientCreate(BaseModel):
    name: str
    age: int
    gender: str
    vitals: Dict[str, Any] = Field(default_factory=dict)
    consultation_reason: str

class Appointment(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    patient_id: str
    provider_id: str
    doctor_id: Optional[str] = None
    appointment_type: str  # "emergency" or "non_emergency"
    status: str = Field(default="pending")  # pending, accepted, completed, cancelled
    consultation_notes: Optional[str] = None
    doctor_notes: Optional[str] = None  # Notes from doctor to provider
    scheduled_time: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class AppointmentCreate(BaseModel):
    patient: PatientCreate
    appointment_type: str
    consultation_notes: Optional[str] = None

class AppointmentUpdate(BaseModel):
    status: Optional[str] = None
    doctor_id: Optional[str] = None
    consultation_notes: Optional[str] = None
    doctor_notes: Optional[str] = None  # Notes from doctor to provider
    scheduled_time: Optional[datetime] = None

class AppointmentNote(BaseModel):
    note: str
    sender_role: str  # doctor or provider
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class Token(BaseModel):
    access_token: str
    token_type: str
    user: Dict[str, Any]

class VideoCallSession(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    appointment_id: str
    provider_id: str
    doctor_id: Optional[str] = None
    session_token: str
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    ended_at: Optional[datetime] = None

class PushSubscription(BaseModel):
    endpoint: str
    keys: Dict[str, str]  # Contains p256dh and auth keys
    
class UserPushSubscription(BaseModel):
    user_id: str
    subscription: PushSubscription
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    active: bool = True

class PushNotificationPayload(BaseModel):
    title: str
    body: str
    icon: str = "/icons/icon-192x192.png"
    badge: str = "/icons/badge-72x72.png"
    data: Optional[Dict[str, Any]] = None
    type: str = "info"  # info, emergency, video_call, appointment_reminder

# Push notification helper functions
async def send_push_notification(user_id: str, payload: PushNotificationPayload):
    """Send push notification to a specific user."""
    try:
        # Get user's push subscriptions
        subscriptions = await db.push_subscriptions.find({"user_id": user_id, "active": True}).to_list(None)
        
        if not subscriptions:
            return False
        
        notification_data = {
            "title": payload.title,
            "body": payload.body,
            "icon": payload.icon,
            "badge": payload.badge,
            "data": payload.data or {},
            "type": payload.type
        }
        
        success_count = 0
        for sub_doc in subscriptions:
            try:
                subscription = sub_doc["subscription"]
                
                response = webpush(
                    subscription_info={
                        "endpoint": subscription["endpoint"],
                        "keys": subscription["keys"]
                    },
                    data=json.dumps(notification_data),
                    vapid_private_key=VAPID_PRIVATE_KEY,
                    vapid_claims=VAPID_CLAIMS
                )
                
                if response.status_code in [200, 201, 204]:
                    success_count += 1
                else:
                    # Mark subscription as inactive if it fails
                    await db.push_subscriptions.update_one(
                        {"_id": sub_doc["_id"]},
                        {"$set": {"active": False}}
                    )
                    
            except WebPushException as e:
                print(f"Push notification failed for user {user_id}: {e}")
                # Mark subscription as inactive
                await db.push_subscriptions.update_one(
                    {"_id": sub_doc["_id"]},
                    {"$set": {"active": False}}
                )
            except Exception as e:
                print(f"Unexpected error sending push notification: {e}")
                
        return success_count > 0
        
    except Exception as e:
        print(f"Error sending push notification to user {user_id}: {e}")
        return False

async def send_appointment_reminder_notifications(appointment_id: str):
    """Send appointment reminder notifications to relevant users."""
    try:
        appointment = await db.appointments.find_one({"id": appointment_id})
        if not appointment:
            return
            
        provider_id = appointment["provider_id"]
        doctor_id = appointment.get("doctor_id")
        
        # Send to provider
        provider_payload = PushNotificationPayload(
            title="Appointment Reminder",
            body=f"You have an upcoming {appointment['appointment_type']} appointment",
            type="appointment_reminder",
            data={
                "appointment_id": appointment_id,
                "action": "view_appointment"
            }
        )
        await send_push_notification(provider_id, provider_payload)
        
        # Send to doctor if assigned
        if doctor_id:
            doctor_payload = PushNotificationPayload(
                title="Appointment Reminder", 
                body=f"You have an upcoming consultation with {appointment['patient_name']}",
                type="appointment_reminder",
                data={
                    "appointment_id": appointment_id,
                    "action": "view_appointment"
                }
            )
            await send_push_notification(doctor_id, doctor_payload)
            
    except Exception as e:
        print(f"Error sending appointment reminders: {e}")

async def send_video_call_notification(appointment_id: str, caller_role: str):
    """Send push notification for video call invitation."""
    try:
        appointment = await db.appointments.find_one({"id": appointment_id})
        if not appointment:
            return
            
        provider_id = appointment["provider_id"]
        doctor_id = appointment.get("doctor_id")
        
        # Determine who to notify based on caller
        if caller_role == "doctor" and provider_id:
            target_user_id = provider_id
            caller_name = "Doctor"
        elif caller_role == "provider" and doctor_id:
            target_user_id = doctor_id
            caller_name = "Provider"
        else:
            return
            
        payload = PushNotificationPayload(
            title="Incoming Video Call",
            body=f"{caller_name} is inviting you to a video consultation",
            type="video_call",
            data={
                "appointment_id": appointment_id,
                "action": "join_call",
                "caller_role": caller_role
            }
        )
        
        await send_push_notification(target_user_id, payload)
        
    except Exception as e:
        print(f"Error sending video call notification: {e}")


# Utility functions
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    
    user = await db.users.find_one({"username": username})
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")
    return User(**user)

# Authentication endpoints
@api_router.post("/register", response_model=User)
async def register_user(user: UserCreate):
    # Check if user already exists
    existing_user = await db.users.find_one({"$or": [{"username": user.username}, {"email": user.email}]})
    if existing_user:
        raise HTTPException(status_code=400, detail="Username or email already exists")
    
    # Hash password and create user
    hashed_password = get_password_hash(user.password)
    user_dict = user.dict()
    del user_dict["password"]
    
    new_user = User(**user_dict)
    user_data = new_user.dict()
    user_data["hashed_password"] = hashed_password
    
    await db.users.insert_one(user_data)
    return new_user

@api_router.post("/admin/create-user", response_model=User)
async def create_user_admin(user: UserCreate, current_user: User = Depends(get_current_user)):
    # Only admins can create new users
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required to create users")
    
    # Check if user already exists
    existing_user = await db.users.find_one({"$or": [{"username": user.username}, {"email": user.email}]})
    if existing_user:
        raise HTTPException(status_code=400, detail="Username or email already exists")
    
    # Hash password and create user
    hashed_password = get_password_hash(user.password)
    user_dict = user.dict()
    del user_dict["password"]
    
    new_user = User(**user_dict)
    user_data = new_user.dict()
    user_data["hashed_password"] = hashed_password
    
    await db.users.insert_one(user_data)
    return new_user

@api_router.post("/login", response_model=Token)
async def login_user(user_login: UserLogin):
    user = await db.users.find_one({"username": user_login.username})
    if not user or not verify_password(user_login.password, user["hashed_password"]):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    if not user.get("is_active", True):
        raise HTTPException(status_code=401, detail="Account is deactivated")
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["username"]}, expires_delta=access_token_expires
    )
    
    user_data = {k: v for k, v in user.items() if k not in ["hashed_password", "_id"]}
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user_data
    }

# User management endpoints
@api_router.get("/users", response_model=List[User])
async def get_users(current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    users = await db.users.find().to_list(1000)
    return [User(**{k: v for k, v in user.items() if k != "hashed_password"}) for user in users]

@api_router.get("/users/{user_role}", response_model=List[User])
async def get_users_by_role(user_role: str, current_user: User = Depends(get_current_user)):
    users = await db.users.find({"role": user_role, "is_active": True}).to_list(1000)
    return [User(**{k: v for k, v in user.items() if k != "hashed_password"}) for user in users]

@api_router.delete("/users/{user_id}")
async def delete_user(user_id: str, current_user: User = Depends(get_current_user)):
    # Only admins can delete users
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Prevent self-deletion
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot delete your own account")
    
    # Check if user exists
    user_to_delete = await db.users.find_one({"id": user_id})
    if not user_to_delete:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Delete the user
    result = await db.users.delete_one({"id": user_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {"message": f"User {user_to_delete['full_name']} deleted successfully"}

@api_router.put("/users/{user_id}/status")
async def update_user_status(user_id: str, status_update: dict, current_user: User = Depends(get_current_user)):
    # Only admins can update user status
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Prevent self-deactivation
    if user_id == current_user.id and not status_update.get("is_active", True):
        raise HTTPException(status_code=400, detail="Cannot deactivate your own account")
    
    # Check if user exists
    user_to_update = await db.users.find_one({"id": user_id})
    if not user_to_update:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Update user status
    result = await db.users.update_one(
        {"id": user_id}, 
        {"$set": {"is_active": status_update.get("is_active", True)}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="User not found or no changes made")
    
    action = "activated" if status_update.get("is_active", True) else "deactivated"
    return {"message": f"User {user_to_update['full_name']} {action} successfully"}

@api_router.put("/users/{user_id}")
async def update_user(user_id: str, user_update: dict, current_user: User = Depends(get_current_user)):
    """Update user information (admin only)"""
    # Only admins can update users
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Check if user exists
    existing_user = await db.users.find_one({"id": user_id})
    if not existing_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Prevent changing sensitive fields
    allowed_fields = [
        "full_name", "email", "phone", "district", "specialty", "is_active"
    ]
    
    update_data = {}
    for field, value in user_update.items():
        if field in allowed_fields:
            update_data[field] = value
    
    # Check for duplicate email if email is being updated
    if "email" in update_data and update_data["email"] != existing_user["email"]:
        email_exists = await db.users.find_one({
            "email": update_data["email"],
            "id": {"$ne": user_id}
        })
        if email_exists:
            raise HTTPException(status_code=400, detail="Email already exists")
    
    if not update_data:
        raise HTTPException(status_code=400, detail="No valid fields to update")
    
    # Add updated timestamp
    update_data["updated_at"] = datetime.now(timezone.utc)
    
    # Update user
    result = await db.users.update_one(
        {"id": user_id},
        {"$set": update_data}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Return updated user
    updated_user = await db.users.find_one({"id": user_id})
    return {k: v for k, v in updated_user.items() if k not in ["hashed_password", "_id"]}

# Appointment endpoints
@api_router.post("/appointments", response_model=Appointment)
async def create_appointment(appointment_data: AppointmentCreate, current_user: User = Depends(get_current_user)):
    if current_user.role != "provider":
        raise HTTPException(status_code=403, detail="Only providers can create appointments")
    
    # Create patient record
    patient = Patient(**appointment_data.patient.dict())
    await db.patients.insert_one(patient.dict())
    
    # Create appointment
    appointment = Appointment(
        patient_id=patient.id,
        provider_id=current_user.id,
        appointment_type=appointment_data.appointment_type,
        consultation_notes=appointment_data.consultation_notes
    )
    
    await db.appointments.insert_one(appointment.dict())
    
    # Send notification to doctors if emergency
    if appointment_data.appointment_type == "emergency":
        doctors = await db.users.find({"role": "doctor", "is_active": True}).to_list(1000)
        notification = {
            "type": "emergency_appointment",
            "appointment_id": appointment.id,
            "patient_name": patient.name,
            "provider_name": current_user.full_name,
            "provider_district": current_user.district,
            "consultation_reason": patient.consultation_reason,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        for doctor in doctors:
            await manager.send_personal_message(notification, doctor["id"])
    
    return appointment

@api_router.get("/appointments", response_model=List[dict])
async def get_appointments(current_user: User = Depends(get_current_user)):
    if current_user.role == "provider":
        # Providers can only see their own appointments
        appointments = await db.appointments.find({"provider_id": current_user.id}).to_list(1000)
    elif current_user.role == "doctor":
        # Doctors can see all pending appointments + their accepted appointments
        appointments = await db.appointments.find({
            "$or": [
                {"status": "pending"},
                {"doctor_id": current_user.id}
            ]
        }).to_list(1000)
    elif current_user.role == "admin":
        # Admins can see all appointments
        appointments = await db.appointments.find().to_list(1000)
    else:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Enrich with patient and user details
    enriched_appointments = []
    for appointment in appointments:
        # Remove MongoDB _id field from appointment
        appointment = {k: v for k, v in appointment.items() if k != "_id"}
        
        patient = await db.patients.find_one({"id": appointment["patient_id"]})
        provider = await db.users.find_one({"id": appointment["provider_id"]})
        doctor = None
        if appointment.get("doctor_id"):
            doctor = await db.users.find_one({"id": appointment["doctor_id"]})
        
        enriched_appointment = {
            **appointment,
            "patient": {k: v for k, v in patient.items() if k != "_id"} if patient else None,
            "provider": {k: v for k, v in provider.items() if k not in ["hashed_password", "_id"]} if provider else None,
            "doctor": {k: v for k, v in doctor.items() if k not in ["hashed_password", "_id"]} if doctor else None
        }
        enriched_appointments.append(enriched_appointment)
    
    return enriched_appointments

@api_router.put("/appointments/{appointment_id}", response_model=Appointment)
async def update_appointment(appointment_id: str, update_data: AppointmentUpdate, current_user: User = Depends(get_current_user)):
    appointment = await db.appointments.find_one({"id": appointment_id})
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    # Role-based permissions
    if current_user.role == "doctor":
        # Doctors can update appointments (accept, add notes, etc.)
        pass
    elif current_user.role == "provider":
        # Providers can only update their own appointments (cancel, etc.)
        if appointment["provider_id"] != current_user.id:
            raise HTTPException(status_code=403, detail="You can only update your own appointments")
    elif current_user.role == "admin":
        # Admins can update any appointment
        pass
    else:
        raise HTTPException(status_code=403, detail="Access denied")
    
    update_dict = update_data.dict(exclude_unset=True)
    if update_dict:
        update_dict["updated_at"] = datetime.now(timezone.utc)
        await db.appointments.update_one({"id": appointment_id}, {"$set": update_dict})
    
    updated_appointment = await db.appointments.find_one({"id": appointment_id})
    
    # Send notifications for important updates
    if update_dict:
        # Get appointment details for notifications
        patient = appointment.get("patient", {})
        
        # If status changed to accepted by doctor, notify provider
        if update_dict.get("status") == "accepted" and current_user.role == "doctor":
            provider_id = appointment.get("provider_id")
            if provider_id:
                notification = {
                    "type": "appointment_accepted",
                    "appointment_id": appointment_id,
                    "patient_name": patient.get("name", "Unknown"),
                    "doctor_name": current_user.full_name,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                await manager.send_personal_message(notification, provider_id)
        
        # If any update is made, notify relevant parties
        general_notification = {
            "type": "appointment_updated",
            "appointment_id": appointment_id,
            "patient_name": patient.get("name", "Unknown"),
            "updated_by": current_user.full_name,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Notify provider if they're not the one making the update
        provider_id = appointment.get("provider_id")
        if provider_id and provider_id != current_user.id:
            await manager.send_personal_message(general_notification, provider_id)
        
        # Notify doctor if they're assigned and not the one making the update  
        doctor_id = appointment.get("doctor_id")
        if doctor_id and doctor_id != current_user.id:
            await manager.send_personal_message(general_notification, doctor_id)
    
    return Appointment(**updated_appointment)

@api_router.post("/appointments/{appointment_id}/notes")
async def add_appointment_note(appointment_id: str, note_data: AppointmentNote, current_user: User = Depends(get_current_user)):
    """Add a note to an appointment"""
    appointment = await db.appointments.find_one({"id": appointment_id})
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    # Only doctors and providers involved in the appointment can add notes
    if current_user.role == "doctor":
        # Doctors can add notes to:
        # 1. Appointments they are assigned to (doctor_id matches)
        # 2. Pending appointments (doctor_id is None) - they can communicate before accepting
        if appointment.get("doctor_id") and appointment.get("doctor_id") != current_user.id:
            raise HTTPException(status_code=403, detail="You can only add notes to your appointments")
    elif current_user.role == "provider":
        if appointment["provider_id"] != current_user.id:
            raise HTTPException(status_code=403, detail="You can only add notes to your appointments")
    else:
        raise HTTPException(status_code=403, detail="Only doctors and providers can add notes")
    
    # Create note document
    note_doc = {
        "id": str(uuid.uuid4()),
        "appointment_id": appointment_id,
        "sender_id": current_user.id,
        "sender_name": current_user.full_name,
        "sender_role": current_user.role,
        "note": note_data.note,
        "timestamp": datetime.now(timezone.utc)
    }
    
    await db.appointment_notes.insert_one(note_doc)
    
    # Update appointment with latest note
    if current_user.role == "doctor":
        await db.appointments.update_one(
            {"id": appointment_id}, 
            {"$set": {"doctor_notes": note_data.note, "updated_at": datetime.now(timezone.utc)}}
        )
    
    return {"message": "Note added successfully", "note_id": note_doc["id"]}

@api_router.get("/appointments/{appointment_id}/notes")
async def get_appointment_notes(appointment_id: str, current_user: User = Depends(get_current_user)):
    """Get all notes for an appointment"""
    appointment = await db.appointments.find_one({"id": appointment_id})
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    # Check permissions
    if current_user.role == "doctor":
        # Doctors can see notes for appointments they're involved in
        if appointment.get("doctor_id") != current_user.id and appointment.get("status") == "pending":
            # Allow doctors to see notes for pending appointments they might accept
            pass
    elif current_user.role == "provider":
        if appointment["provider_id"] != current_user.id:
            raise HTTPException(status_code=403, detail="You can only view notes for your appointments")
    elif current_user.role == "admin":
        # Admins can see all notes
        pass
    else:
        raise HTTPException(status_code=403, detail="Access denied")
    
    notes = await db.appointment_notes.find({"appointment_id": appointment_id}).to_list(1000)
    
    # Clean MongoDB ObjectId fields
    cleaned_notes = []
    for note in notes:
        cleaned_note = {k: v for k, v in note.items() if k != "_id"}
        cleaned_notes.append(cleaned_note)
    
    return sorted(cleaned_notes, key=lambda x: x["timestamp"])

@api_router.delete("/appointments/{appointment_id}")
async def delete_appointment(appointment_id: str, current_user: User = Depends(get_current_user)):
    """Delete an appointment"""
    appointment = await db.appointments.find_one({"id": appointment_id})
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    # Role-based permissions
    if current_user.role == "admin":
        # Admins can delete any appointment
        pass
    elif current_user.role == "provider":
        # Providers can only delete their own appointments if they're pending or not yet started
        if appointment["provider_id"] != current_user.id:
            raise HTTPException(status_code=403, detail="You can only delete your own appointments")
        if appointment["status"] not in ["pending", "accepted"]:
            raise HTTPException(status_code=400, detail="Cannot delete completed appointments")
    else:
        raise HTTPException(status_code=403, detail="Only admins and providers can delete appointments")
    
    # Delete appointment and related data
    await db.appointments.delete_one({"id": appointment_id})
    await db.appointment_notes.delete_many({"appointment_id": appointment_id})
    await db.patients.delete_one({"id": appointment["patient_id"]})
    
    return {"message": "Appointment deleted successfully"}

@api_router.get("/appointments/{appointment_id}")
async def get_appointment_details(appointment_id: str, current_user: User = Depends(get_current_user)):
    """Get detailed appointment information"""
    appointment = await db.appointments.find_one({"id": appointment_id})
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    # Check permissions
    if current_user.role == "doctor":
        # Doctors can view any appointment details
        pass
    elif current_user.role == "provider":
        if appointment["provider_id"] != current_user.id:
            raise HTTPException(status_code=403, detail="You can only view your own appointments")
    elif current_user.role == "admin":
        # Admins can view any appointment
        pass
    else:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Enrich with related data
    patient = await db.patients.find_one({"id": appointment["patient_id"]})
    provider = await db.users.find_one({"id": appointment["provider_id"]})
    doctor = None
    if appointment.get("doctor_id"):
        doctor = await db.users.find_one({"id": appointment["doctor_id"]})
    
    notes = await db.appointment_notes.find({"appointment_id": appointment_id}).to_list(1000)
    
    # Clean MongoDB ObjectId fields from all data
    def clean_mongo_data(data):
        if isinstance(data, dict):
            return {k: v for k, v in data.items() if k != "_id"}
        elif isinstance(data, list):
            return [clean_mongo_data(item) for item in data]
        else:
            return data
    
    return {
        **clean_mongo_data(appointment),
        "patient": clean_mongo_data(patient) if patient else None,
        "provider": clean_mongo_data(provider) if provider else None,
        "doctor": clean_mongo_data(doctor) if doctor else None,
        "notes": clean_mongo_data(notes) if notes else []
    }

# Video call endpoints
@api_router.post("/video-call/start/{appointment_id}")
async def start_video_call(appointment_id: str, current_user: User = Depends(get_current_user)):
    appointment = await db.appointments.find_one({"id": appointment_id})
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    # Generate session token
    session_token = str(uuid.uuid4())
    
    # Create video call session
    video_session = VideoCallSession(
        appointment_id=appointment_id,
        provider_id=appointment["provider_id"],
        doctor_id=current_user.id if current_user.role == "doctor" else appointment.get("doctor_id"),
        session_token=session_token
    )
    
    await db.video_sessions.insert_one(video_session.dict())
    
    # Notify the other participant
    if current_user.role == "doctor":
        target_user_id = appointment["provider_id"]
    else:
        target_user_id = appointment.get("doctor_id")
    
    if target_user_id:
        notification = {
            "type": "video_call_invitation",
            "session_token": session_token,
            "appointment_id": appointment_id,
            "caller": current_user.full_name,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        await manager.send_personal_message(notification, target_user_id)
        
        # Send push notification
        await send_video_call_notification(appointment_id, current_user.role)
    
    return {"session_token": session_token, "appointment_id": appointment_id}

@api_router.get("/video-call/session/{appointment_id}")
async def get_video_call_session(appointment_id: str, current_user: User = Depends(get_current_user)):
    """Get or create Jitsi room for appointment"""
    appointment = await db.appointments.find_one({"id": appointment_id})
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    # Check if user is authorized to access this appointment
    if current_user.role == "doctor":
        # Doctors can access any appointment they're assigned to or if no doctor is assigned yet
        if appointment.get("doctor_id") and appointment.get("doctor_id") != current_user.id:
            raise HTTPException(status_code=403, detail="You are not assigned to this appointment")
    elif current_user.role == "provider":
        # Providers can only access their own appointments
        if appointment["provider_id"] != current_user.id:
            raise HTTPException(status_code=403, detail="You can only access your own appointments")
    else:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Generate Jitsi room name based on appointment ID
    room_name = f"greenstar-appointment-{appointment_id}"
    
    # Create Jitsi meeting URL
    jitsi_domain = "meet.jit.si"  # Using public Jitsi server
    jitsi_url = f"https://{jitsi_domain}/{room_name}"
    
    # Store the Jitsi room info
    jitsi_session = {
        "appointment_id": appointment_id,
        "room_name": room_name,
        "jitsi_url": jitsi_url,
        "created_by": current_user.id,
        "created_at": datetime.now(timezone.utc),
        "participants": []
    }
    
    # Update or insert Jitsi session
    await db.jitsi_sessions.update_one(
        {"appointment_id": appointment_id},
        {"$set": jitsi_session},
        upsert=True
    )
    
    # Notify the other participant about video call invitation
    if current_user.role == "doctor":
        target_user_id = appointment.get("provider_id")
    else:
        target_user_id = appointment.get("doctor_id")
    
    if target_user_id:
        # Get appointment details for notification
        patient_info = appointment.get("patient", {})
        
        notification = {
            "type": "jitsi_call_invitation",
            "appointment_id": appointment_id,
            "jitsi_url": jitsi_url,
            "room_name": room_name,
            "caller": current_user.full_name,
            "caller_role": current_user.role,
            "appointment_type": appointment.get("appointment_type", "non_emergency"),
            "patient": {
                "name": patient_info.get("name", "Unknown Patient"),
                "age": patient_info.get("age", "Unknown"),
                "gender": patient_info.get("gender", "Unknown"),
                "consultation_reason": patient_info.get("consultation_reason", "General consultation"),
                "vitals": patient_info.get("vitals", {})
            },
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        await manager.send_personal_message(notification, target_user_id)
    
    return {
        "jitsi_url": jitsi_url,
        "room_name": room_name,
        "appointment_id": appointment_id,
        "status": "ready"
    }

@api_router.post("/video-call/end/{room_name}")
async def end_jitsi_call(room_name: str, current_user: User = Depends(get_current_user)):
    """End a Jitsi video call session"""
    jitsi_session = await db.jitsi_sessions.find_one({"room_name": room_name})
    if not jitsi_session:
        raise HTTPException(status_code=404, detail="Jitsi session not found")
    
    # Mark session as ended
    await db.jitsi_sessions.update_one(
        {"room_name": room_name},
        {"$set": {"ended_at": datetime.now(timezone.utc)}}
    )
    
    return {"message": "Jitsi call session ended successfully"}

@api_router.get("/video-call/join/{session_token}")
async def join_video_call(session_token: str, current_user: User = Depends(get_current_user)):
    # Find the video session
    video_session = await db.video_sessions.find_one({"session_token": session_token})
    if not video_session:
        raise HTTPException(status_code=404, detail="Video session not found")
    
    # Get the associated appointment
    appointment = await db.appointments.find_one({"id": video_session["appointment_id"]})
    if not appointment:
        raise HTTPException(status_code=404, detail="Associated appointment not found")
    
    # Check if user is authorized to join this call
    if current_user.role == "doctor":
        if video_session.get("doctor_id") and video_session["doctor_id"] != current_user.id:
            raise HTTPException(status_code=403, detail="You are not authorized to join this call")
    elif current_user.role == "provider":
        if video_session["provider_id"] != current_user.id:
            raise HTTPException(status_code=403, detail="You are not authorized to join this call")
    else:
        raise HTTPException(status_code=403, detail="Only doctors and providers can join video calls")
    
    # Return session and appointment details (clean MongoDB ObjectId fields)
    def clean_mongo_data(data):
        if isinstance(data, dict):
            return {k: v for k, v in data.items() if k != "_id"}
        elif isinstance(data, list):
            return [clean_mongo_data(item) for item in data]
        else:
            return data
    
    return {
        "session_token": session_token,
        "appointment_id": video_session["appointment_id"],
        "appointment": clean_mongo_data(appointment),
        "video_session": clean_mongo_data(video_session)
    }

# WebSocket endpoint for real-time notifications (dashboard notifications only)
@app.websocket("/api/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    await manager.connect(websocket, user_id)
    try:
        while True:
            data = await websocket.receive_text()
            # Handle incoming messages if needed
    except WebSocketDisconnect:
        manager.disconnect(user_id)

# Push notification endpoints
@api_router.post("/push/subscribe")
async def subscribe_to_push_notifications(subscription_data: UserPushSubscription, current_user: User = Depends(get_current_user)):
    """Subscribe user to push notifications."""
    try:
        # Remove any existing subscriptions for this user to avoid duplicates
        await db.push_subscriptions.delete_many({"user_id": current_user.id})
        
        # Add new subscription
        subscription_doc = {
            "user_id": current_user.id,
            "subscription": subscription_data.subscription.dict(),
            "created_at": datetime.now(timezone.utc),
            "active": True
        }
        
        result = await db.push_subscriptions.insert_one(subscription_doc)
        
        if result.inserted_id:
            return {"message": "Successfully subscribed to push notifications", "success": True}
        else:
            raise HTTPException(status_code=500, detail="Failed to subscribe to push notifications")
            
    except Exception as e:
        print(f"Error subscribing user to push notifications: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@api_router.delete("/push/unsubscribe")
async def unsubscribe_from_push_notifications(current_user: User = Depends(get_current_user)):
    """Unsubscribe user from push notifications."""
    try:
        result = await db.push_subscriptions.delete_many({"user_id": current_user.id})
        return {"message": f"Unsubscribed from {result.deleted_count} push notification subscriptions", "success": True}
    except Exception as e:
        print(f"Error unsubscribing user from push notifications: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@api_router.get("/push/vapid-key")
async def get_vapid_public_key():
    """Get VAPID public key for push notification subscription."""
    return {"vapid_public_key": VAPID_PUBLIC_KEY}

@api_router.post("/push/test")
async def send_test_push_notification(current_user: User = Depends(get_current_user)):
    """Send a test push notification to the current user."""
    try:
        payload = PushNotificationPayload(
            title="Test Notification",
            body="This is a test push notification from Greenstar Telehealth",
            type="info",
            data={"test": True}
        )
        
        success = await send_push_notification(current_user.id, payload)
        
        if success:
            return {"message": "Test notification sent successfully", "success": True}
        else:
            return {"message": "No active push subscriptions found or notification failed", "success": False}
            
    except Exception as e:
        print(f"Error sending test push notification: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@api_router.post("/push/appointment-reminder/{appointment_id}")
async def send_appointment_reminder(appointment_id: str, current_user: User = Depends(get_current_user)):
    """Send appointment reminder push notifications (admin only)."""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can send appointment reminders")
    
    try:
        await send_appointment_reminder_notifications(appointment_id)
        return {"message": "Appointment reminder notifications sent", "success": True}
    except Exception as e:
        print(f"Error sending appointment reminder: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Basic health check
@api_router.get("/health")
async def health_check():
    return {"status": "healthy", "message": "Greenstar Telehealth API is running"}

@api_router.get("/")
async def root():
    return {"message": "MedConnect Telehealth API is running"}

# Video Call WebSocket endpoint
@app.websocket("/api/ws/video-call/{session_token}")
async def video_call_websocket(websocket: WebSocket, session_token: str):
    try:
        # Validate session token exists in video_sessions
        session_exists = await db.video_sessions.find_one({"session_token": session_token})
        if not session_exists:
            print(f"❌ Invalid session token: {session_token}")
            await websocket.close(code=4000, reason="Invalid session token")
            return
            
        # Use session token as unique identifier for this call
        user_id = f"user-{session_token[:8]}"
        user_name = f"Participant-{session_token[:8]}"
        
        await websocket.accept()
        print(f"✅ Video call WebSocket accepted: session={session_token}, user={user_id}")
        
        if session_token not in video_call_manager.active_sessions:
            video_call_manager.active_sessions[session_token] = {}
        
        video_call_manager.active_sessions[session_token][user_id] = websocket
        
        # Send welcome message
        await websocket.send_text(json.dumps({
            "type": "connection-established",
            "session": session_token,
            "userId": user_id
        }))
        
        print(f"🔌 Video call session active: {len(video_call_manager.active_sessions[session_token])} participants")
        
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            print(f"📡 Video call message from {user_id}: {message.get('type', 'unknown')}")
            
            # Relay WebRTC signaling messages to other participants
            await video_call_manager.relay_message(session_token, user_id, message)
            
    except WebSocketDisconnect:
        print(f"📡 Video call WebSocket disconnected: session={session_token}")
        if session_token in video_call_manager.active_sessions:
            user_id = f"user-{session_token[:8]}"
            video_call_manager.leave_session(session_token, user_id)
    except Exception as e:
        print(f"❌ Video call WebSocket error: {e}")
        await websocket.close(code=1011, reason=str(e))

# Test WebSocket endpoint
@app.websocket("/test-ws")
async def test_websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    await websocket.send_text("Test WebSocket connected!")
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(f"Echo: {data}")
    except WebSocketDisconnect:
        pass

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()