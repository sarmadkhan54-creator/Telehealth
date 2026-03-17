# Greenstar Telehealth Platform - Product Requirements Document

## Original Problem Statement
Full-stack telehealth platform enabling video consultations between healthcare providers and doctors. Features include:
- Provider dashboard for creating appointments (emergency/non-emergency)
- Doctor dashboard for viewing and accepting appointments
- Real-time video calling using Jitsi Meet
- Real-time notifications via WebSocket
- Admin dashboard for user management

## Core Requirements
1. **Authentication**: JWT-based login with role-based access (provider, doctor, admin)
2. **Real-time Communication**: WebSocket for instant notifications (calls, appointments, notes)
3. **Video Calling**: Jitsi Meet integration for emergency appointments
4. **Notification System**: Browser notifications and in-app notification panel

## Tech Stack
- **Frontend**: React.js with Tailwind CSS
- **Backend**: FastAPI (Python)
- **Database**: MongoDB
- **Real-time**: WebSocket + 2-second polling fallback
- **Video**: Jitsi Meet

## What's Been Implemented

### Session: January 2026 - Video Call Notification Fix

**Issues Fixed:**
1. **WebSocket Not Connecting** (P0)
   - Root Cause: `setupWebSocket()` function was defined but never called
   - Fix: Added useEffect hook at Dashboard.js lines 83-96 to call setupWebSocket() when user is available
   - File: `frontend/src/components/Dashboard.js`

2. **Content Security Policy Blocking API Calls** (P0)
   - Root Cause: CSP `connect-src` only allowed `'self' wss: ws:`, blocking `https:` calls
   - Fix: Added `https:` to connect-src directive
   - File: `frontend/public/index.html` line 38

3. **Custom Domain URL Configuration**
   - Fix: Updated `config.js` to prioritize custom domain detection over env variable
   - Custom domains (like telehealthapp.online) now correctly use production backend
   - File: `frontend/src/config.js`

**Verified Working:**
- Provider login and WebSocket connection
- Doctor initiating video calls
- Provider receiving incoming call notifications
- Call notification popup with Answer/Decline
- Call cancellation when doctor closes window
- 2-second polling for appointment updates
- **Real-time data synchronization** - Appointments created by one user appear on other dashboards within 2 seconds via polling

## Test Credentials
- Provider: `testprovider` / `test123`
- Doctor: `testdoctor` / `test123`  
- Admin: `sarmad` / `sarmad`

## Key API Endpoints
- `POST /api/login` - User authentication
- `GET /api/appointments` - List appointments
- `POST /api/video-call/start/{id}` - Initiate video call
- `POST /api/video-call/cancel/{id}` - Cancel video call
- `WS /api/ws/{user_id}` - WebSocket connection

## Prioritized Backlog

### P1 - High Priority
- [ ] Stable WebSocket implementation (replace aggressive polling)
- [ ] Push notifications via Firebase Cloud Messaging

### P2 - Medium Priority
- [ ] Notification panel swipe actions (mark read/delete)
- [ ] Improved mobile responsiveness

### P3 - Low Priority
- [ ] Health check endpoints returning proper JSON (currently HTML)
- [ ] Code refactoring (separate routes, models into files)

## Architecture Notes
```
/app/
├── backend/
│   ├── server.py          # Main FastAPI application
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Dashboard.js        # Provider dashboard
│   │   │   ├── DoctorDashboard.js  # Doctor dashboard
│   │   │   ├── AdminDashboard.js   # Admin dashboard
│   │   │   └── LoginPage.js        # Login page
│   │   └── config.js               # Backend URL config
│   └── public/
│       └── index.html              # CSP headers
└── memory/
    └── PRD.md
```
