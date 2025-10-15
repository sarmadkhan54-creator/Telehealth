// Firebase Configuration for Cloud Messaging
// TODO: Replace with your actual Firebase credentials from https://console.firebase.google.com

const firebaseConfig = {
  apiKey: "AIzaSyDEMO_KEY_REPLACE_THIS",
  authDomain: "telehealth-demo.firebaseapp.com",
  projectId: "telehealth-demo",
  storageBucket: "telehealth-demo.appspot.com",
  messagingSenderId: "123456789012",
  appId: "1:123456789012:web:demo123456789",
  measurementId: "G-DEMO123456"
};

// VAPID Key for Web Push (Get from Firebase Console > Cloud Messaging > Web Push certificates)
const vapidKey = "DEMO_VAPID_KEY_REPLACE_THIS_WITH_YOUR_REAL_KEY";

export { firebaseConfig, vapidKey };
