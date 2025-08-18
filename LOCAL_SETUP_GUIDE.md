# 🌟 Greenstar Telehealth Platform - Local Setup Guide

## 📋 **Complete Application Package**

This package contains your complete Greenstar Telehealth Platform with all source code, configurations, and setup instructions.

### 🏗️ **Project Structure**
```
greenstar-telehealth/
├── backend/
│   ├── server.py                 # Complete FastAPI application
│   ├── requirements.txt          # Python dependencies
│   └── .env.example             # Environment template
├── frontend/
│   ├── src/
│   │   ├── components/          # All React components
│   │   ├── App.js              # Main application
│   │   └── App.css             # Complete styling
│   ├── package.json            # Node.js dependencies
│   ├── tailwind.config.js      # Tailwind configuration
│   └── public/                 # Static assets
├── DEMO_CREDENTIALS.md         # Working demo accounts
└── LOCAL_SETUP_GUIDE.md        # This file
```

## ⚙️ **Prerequisites**
Install these on your computer:
- **Python 3.8+** - [Download Python](https://python.org)
- **Node.js 16+** - [Download Node.js](https://nodejs.org) 
- **MongoDB** - [Download MongoDB](https://mongodb.com) or use MongoDB Atlas
- **Git** - [Download Git](https://git-scm.com)

## 🚀 **Quick Setup (5 Minutes)**

### **Step 1: Backend Setup**
```bash
# Navigate to backend directory
cd backend

# Create Python virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On Mac/Linux:
source venv/bin/activate

# Install all dependencies
pip install -r requirements.txt

# Create environment file
cp .env.example .env
# Edit .env with your database URL

# Start backend server
uvicorn server:app --reload --host 0.0.0.0 --port 8000
```

### **Step 2: Frontend Setup (New Terminal)**
```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install
# or if you prefer yarn:
yarn install

# Start frontend development server
npm start
# or with yarn:
yarn start
```

### **Step 3: Access Your Application**
- **Frontend:** http://localhost:3000
- **Backend API:** http://localhost:8000/docs (API documentation)

## 🔐 **Demo Credentials**
Use these accounts to test your local application:

- **Provider:** `demo_provider` / `Demo123!`
- **Doctor:** `demo_doctor` / `Demo123!`
- **Admin:** `demo_admin` / `Demo123!`

## 🗄️ **Database Setup**

### **Option A: Local MongoDB**
1. Install MongoDB Community Edition
2. Start MongoDB service
3. Database will be created automatically

### **Option B: MongoDB Atlas (Cloud - Recommended)**
1. Create free account at [MongoDB Atlas](https://mongodb.com/atlas)
2. Create new cluster
3. Get connection string
4. Update `MONGODB_URL` in backend/.env

## 📁 **Environment Configuration**

### **Backend (.env file):**
```env
# Database Connection
MONGODB_URL=mongodb://localhost:27017/greenstar_telehealth
# For MongoDB Atlas:
# MONGODB_URL=mongodb+srv://username:password@cluster.mongodb.net/greenstar_telehealth

# JWT Authentication
JWT_SECRET_KEY=your-super-secret-key-change-this-in-production
JWT_ALGORITHM=HS256
JWT_EXPIRATION_HOURS=24

# CORS Settings (for local development)
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

# Application Settings
DB_NAME=greenstar_telehealth
```

### **Frontend (.env file):**
```env
# Backend API URL
REACT_APP_BACKEND_URL=http://localhost:8000

# WebSocket URL (for real-time features)
REACT_APP_WEBSOCKET_URL=ws://localhost:8000
```

## ✅ **Features Included**

Your local setup includes all features from the Emergent version:

### **✅ Complete Authentication System**
- JWT-based login/logout
- Role-based access control (Provider, Doctor, Admin)
- Secure password hashing

### **✅ Provider Features**
- Create emergency/non-emergency appointments
- Comprehensive patient forms with vitals
- Appointment history and status tracking

### **✅ Doctor Features**
- Real-time appointment notifications
- Accept/manage consultations
- Video call integration
- Patient vitals viewing

### **✅ Admin Features**
- User management and creation
- System statistics and reports
- Complete oversight dashboard

### **✅ Technical Features**
- WebSocket real-time notifications
- WebRTC video calling
- MongoDB data persistence
- Responsive tablet-optimized design
- Greenstar branding and styling

## 🚀 **Production Deployment**

Once working locally, you can deploy to:
- **Backend:** Heroku, DigitalOcean, AWS, Railway
- **Frontend:** Netlify, Vercel, or serve from backend
- **Database:** MongoDB Atlas (recommended for production)

## 🔧 **Troubleshooting**

### **Common Issues:**

**Backend won't start:**
- Check if port 8000 is available
- Ensure MongoDB is running
- Verify Python virtual environment is activated

**Frontend won't start:**
- Delete `node_modules` and run `npm install` again  
- Check if port 3000 is available
- Ensure Node.js version is 16+

**Database connection issues:**
- Verify MongoDB is running (local setup)
- Check connection string format (Atlas setup)
- Ensure database name matches in .env

**Login not working:**
- Check backend logs for errors
- Verify JWT secret is set in .env
- Ensure CORS origins include frontend URL

## 📞 **Support**

If you encounter any issues:
1. Check the console logs (browser F12 developer tools)
2. Check backend terminal for error messages
3. Verify all environment variables are set correctly
4. Ensure all dependencies are installed

## 🎉 **Success Verification**

Your setup is working correctly if you can:
1. ✅ Access login page at http://localhost:3000
2. ✅ Login with demo credentials
3. ✅ See appropriate dashboard for each user role
4. ✅ Create appointments as provider
5. ✅ Accept appointments as doctor
6. ✅ Manage users as admin

**Congratulations! You now have the complete Greenstar Telehealth Platform running locally!** 🌟