from fastapi import FastAPI, APIRouter, HTTPException, Depends, status, WebSocket, WebSocketDisconnect
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict, Any
import uuid
from datetime import datetime, timezone, timedelta
import jwt
from passlib.context import CryptContext
import json

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

manager = ConnectionManager()

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
    scheduled_time: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

class AppointmentCreate(BaseModel):
    patient: PatientCreate
    appointment_type: str
    consultation_notes: Optional[str] = None

class AppointmentUpdate(BaseModel):
    status: Optional[str] = None
    doctor_id: Optional[str] = None
    consultation_notes: Optional[str] = None
    scheduled_time: Optional[datetime] = None

class Token(BaseModel):
    access_token: str
    token_type: str
    user: Dict[str, Any]

class VideoCallSession(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    appointment_id: str
    provider_id: str
    doctor_id: str
    session_token: str
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    ended_at: Optional[datetime] = None

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
        appointments = await db.appointments.find({"provider_id": current_user.id}).to_list(1000)
    elif current_user.role == "doctor":
        appointments = await db.appointments.find({"$or": [{"doctor_id": current_user.id}, {"doctor_id": None}]}).to_list(1000)
    elif current_user.role == "admin":
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
    if current_user.role not in ["doctor", "admin"]:
        raise HTTPException(status_code=403, detail="Only doctors can update appointments")
    
    appointment = await db.appointments.find_one({"id": appointment_id})
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    
    update_dict = update_data.dict(exclude_unset=True)
    if update_dict:
        await db.appointments.update_one({"id": appointment_id}, {"$set": update_dict})
    
    updated_appointment = await db.appointments.find_one({"id": appointment_id})
    return Appointment(**updated_appointment)

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
        doctor_id=current_user.id if current_user.role == "doctor" else appointment.get("doctor_id", ""),
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
    
    return {"session_token": session_token, "appointment_id": appointment_id}

# WebSocket endpoint for real-time notifications
@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    await manager.connect(websocket, user_id)
    try:
        while True:
            data = await websocket.receive_text()
            # Handle incoming messages if needed
    except WebSocketDisconnect:
        manager.disconnect(user_id)

# Basic health check
@api_router.get("/")
async def root():
    return {"message": "MedConnect Telehealth API is running"}

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