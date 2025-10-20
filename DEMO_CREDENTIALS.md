# 🌟 Greenstar Telehealth Platform - Demo Credentials

## 🚀 **Application Access**
**Greenstar Telehealth Platform:** Your custom domain (once configured)
**Current URL:** https://medconnect-live-1.preview.emergentagent.com

---

## 🌟 **About Greenstar Healthcare**
**"health • prosperity • future"** - Greenstar Healthcare delivers cutting-edge telehealth solutions connecting healthcare providers with medical professionals for immediate consultations and emergency care.

---

## 👥 **Demo User Accounts**

### 🔧 **Admin User**
- **Username:** `demo_admin`
- **Password:** `Demo123!`
- **Role:** Administrator
- **Access:** Full system management, user creation, reports

### 👨‍⚕️ **Doctor/Consultant**  
- **Username:** `demo_doctor`
- **Password:** `Demo123!`
- **Role:** Doctor
- **Specialty:** General Medicine
- **Access:** View appointments, accept consultations, video calls

### 🏥 **Healthcare Provider**
- **Username:** `demo_provider` 
- **Password:** `Demo123!`
- **Role:** Provider
- **District:** Demo District
- **Access:** Create appointments, patient forms, video calls

---

## 🎯 **How to Test Greenstar Platform**

### **Step 1: Login as Provider**
1. Go to your Greenstar Telehealth Platform URL
2. Login with provider credentials above
3. Create a new appointment (Emergency or Non-Emergency)
4. Fill in patient details and vitals

### **Step 2: Login as Doctor** 
1. Open new incognito/private window
2. Login with doctor credentials
3. See pending appointments from Step 1
4. Accept an appointment
5. Start video call

### **Step 3: Login as Admin**
1. Open another window
2. Login with admin credentials  
3. View system statistics
4. Manage users and appointments
5. Generate reports

---

## 🔥 **Key Features to Test**

### **Emergency Appointments**
- Create emergency appointment as Provider
- Instant notifications to Doctors
- Real-time status updates

### **Bidirectional Communication**
- Doctors and Providers can send notes to each other
- Works for both emergency and non-emergency appointments
- Real-time messaging system

### **Video Calling**
- WebRTC-based video calls
- Screen sharing capabilities
- Call controls (mute, video toggle)

### **Real-time Updates**
- Live appointment statistics
- WebSocket notifications
- Cross-user synchronization

### **Tablet Interface**
- Responsive design for tablets
- Touch-friendly controls
- Professional medical UI

---

## 📱 **Mobile & Tablet Access**
- **Optimal Resolution:** 768x1024 (iPad portrait)
- **Browser:** Chrome, Safari, or Edge
- **Progressive Web App:** Add to home screen for app-like experience
- **Touch Controls:** All buttons sized for touch interaction

---

## 🏆 **Production Features**
✅ **JWT Authentication** - Secure token-based login  
✅ **Role-Based Access** - Different dashboards per user type  
✅ **Real-time Notifications** - WebSocket integration  
✅ **Video Calling** - WebRTC implementation  
✅ **MongoDB Integration** - Scalable data storage  
✅ **Responsive Design** - Tablet-optimized interface  
✅ **Professional UI** - Medical-grade design standards  
✅ **Export Functions** - CSV generation for reports  
✅ **Bidirectional Notes** - Doctor ↔ Provider communication  

---

## 🌐 **Custom Domain Setup Guide**

### **Step 1: Configure DNS**
1. **Go to your DNS provider** (Cloudflare, GoDaddy, etc.)
2. **Add A Record:**
   - **Host:** `telehealth` (or your preferred subdomain)
   - **Points to:** IP address provided by your deployment platform
   - **TTL:** 300 seconds

### **Step 2: Link Domain in Platform**
1. Navigate to Deployments section
2. Click "Link Domain"
3. Enter your domain: `telehealth.yourdomain.com`
4. Wait for verification (5-15 minutes)

### **Step 3: Access Your Custom URL**
- Your Greenstar platform will be accessible at your custom domain
- SSL certificate automatically provided
- Professional branding without platform attribution

---

**🎉 Ready for professional healthcare deployment!**