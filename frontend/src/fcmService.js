// Firebase Cloud Messaging Service
// Handles FCM token generation, permission requests, and message handling

import { initializeApp } from 'firebase/app';
import { getMessaging, getToken, onMessage } from 'firebase/messaging';
import { firebaseConfig, vapidKey } from './firebase-config';
import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Initialize Firebase
let app;
let messaging;

try {
  app = initializeApp(firebaseConfig);
  messaging = getMessaging(app);
  console.log('✅ Firebase initialized successfully');
} catch (error) {
  console.error('❌ Firebase initialization error:', error);
}

/**
 * Request notification permission and get FCM token
 */
export const requestNotificationPermission = async (userId) => {
  try {
    console.log('📱 Requesting notification permission...');
    
    const permission = await Notification.requestPermission();
    console.log('📋 Permission result:', permission);
    
    if (permission === 'granted') {
      console.log('✅ Notification permission granted');
      
      // Register service worker
      if ('serviceWorker' in navigator) {
        try {
          const registration = await navigator.serviceWorker.register('/firebase-messaging-sw.js');
          console.log('✅ Service Worker registered:', registration);
          
          // Get FCM token
          const currentToken = await getToken(messaging, {
            vapidKey: vapidKey,
            serviceWorkerRegistration: registration
          });
          
          if (currentToken) {
            console.log('🔑 FCM Token obtained:', currentToken.substring(0, 20) + '...');
            
            // Save token to backend
            await saveFCMToken(userId, currentToken);
            
            return currentToken;
          } else {
            console.log('⚠️ No FCM token available. Request permission to generate one.');
            return null;
          }
        } catch (error) {
          console.error('❌ Service Worker registration failed:', error);
          return null;
        }
      }
    } else {
      console.log('❌ Notification permission denied');
      return null;
    }
  } catch (error) {
    console.error('❌ Error requesting notification permission:', error);
    return null;
  }
};

/**
 * Save FCM token to backend
 */
const saveFCMToken = async (userId, token) => {
  try {
    const authToken = localStorage.getItem('authToken');
    const response = await axios.post(
      `${API}/fcm/token`,
      {
        user_id: userId,
        fcm_token: token,
        device_type: 'web'
      },
      {
        headers: {
          'Authorization': `Bearer ${authToken}`,
          'Content-Type': 'application/json'
        }
      }
    );
    
    console.log('✅ FCM token saved to backend:', response.data);
    return response.data;
  } catch (error) {
    console.error('❌ Error saving FCM token:', error);
  }
};

/**
 * Handle foreground messages (when app is open)
 */
export const onMessageListener = (callback) => {
  if (!messaging) {
    console.error('❌ Messaging not initialized');
    return;
  }

  onMessage(messaging, (payload) => {
    console.log('🔔 [Foreground] Message received:', payload);
    
    const notificationTitle = payload.notification?.title || 'New Notification';
    const notificationOptions = {
      body: payload.notification?.body || '',
      icon: '/favicon.ico',
      badge: '/favicon.ico',
      tag: payload.data?.type || 'general',
      data: payload.data,
      requireInteraction: payload.data?.type === 'video_call' || payload.data?.type === 'emergency'
    };
    
    console.log('📱 [Foreground] Showing notification:', notificationTitle);
    
    // Show browser notification even in foreground
    if (Notification.permission === 'granted') {
      navigator.serviceWorker.ready.then((registration) => {
        registration.showNotification(notificationTitle, notificationOptions);
      });
    }
    
    // Call the callback with payload
    if (callback) {
      callback(payload);
    }
  });
};

/**
 * Listen for service worker messages (notification clicks)
 */
export const listenForNotificationClicks = (callback) => {
  if ('serviceWorker' in navigator) {
    navigator.serviceWorker.addEventListener('message', (event) => {
      console.log('📬 Message from Service Worker:', event.data);
      
      if (event.data.type === 'NOTIFICATION_CLICK') {
        console.log('🖱️ Notification was clicked, data:', event.data.data);
        
        if (callback) {
          callback(event.data.data);
        }
      }
    });
  }
};

/**
 * Delete FCM token (on logout)
 */
export const deleteFCMToken = async (userId) => {
  try {
    const authToken = localStorage.getItem('authToken');
    await axios.delete(`${API}/fcm/token/${userId}`, {
      headers: {
        'Authorization': `Bearer ${authToken}`
      }
    });
    console.log('✅ FCM token deleted from backend');
  } catch (error) {
    console.error('❌ Error deleting FCM token:', error);
  }
};

export default {
  requestNotificationPermission,
  onMessageListener,
  listenForNotificationClicks,
  deleteFCMToken
};
