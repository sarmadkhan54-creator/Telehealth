// Firebase Cloud Messaging Service Worker
// This handles notifications when app is in background or closed

importScripts('https://www.gstatic.com/firebasejs/10.7.1/firebase-app-compat.js');
importScripts('https://www.gstatic.com/firebasejs/10.7.1/firebase-messaging-compat.js');

// Initialize Firebase in service worker
firebase.initializeApp({
  apiKey: "AIzaSyDEMO_KEY_REPLACE_THIS",
  authDomain: "telehealth-demo.firebaseapp.com",
  projectId: "telehealth-demo",
  storageBucket: "telehealth-demo.appspot.com",
  messagingSenderId: "123456789012",
  appId: "1:123456789012:web:demo123456789"
});

const messaging = firebase.messaging();

// Handle background messages
messaging.onBackgroundMessage((payload) => {
  console.log('🔔 [Service Worker] Background message received:', payload);

  const notificationTitle = payload.notification?.title || 'Telehealth Notification';
  const notificationOptions = {
    body: payload.notification?.body || 'You have a new notification',
    icon: '/favicon.ico',
    badge: '/favicon.ico',
    tag: payload.data?.type || 'general',
    data: payload.data, // Store data for click handling
    requireInteraction: payload.data?.type === 'video_call' || payload.data?.type === 'emergency',
    vibrate: payload.data?.type === 'emergency' ? [200, 100, 200, 100, 200] : [200, 100, 200],
    actions: payload.data?.type === 'video_call' ? [
      { action: 'answer', title: 'Answer' },
      { action: 'decline', title: 'Decline' }
    ] : []
  };

  console.log('📱 [Service Worker] Showing notification:', notificationTitle);
  return self.registration.showNotification(notificationTitle, notificationOptions);
});

// Handle notification click
self.addEventListener('notificationclick', (event) => {
  console.log('🖱️ [Service Worker] Notification clicked:', event.notification.tag);
  console.log('📋 [Service Worker] Notification data:', event.notification.data);

  event.notification.close();

  const data = event.notification.data || {};
  let urlToOpen = '/';

  // Determine which URL to open based on notification type
  switch(data.type) {
    case 'video_call':
    case 'incoming_video_call':
      // Open the video call directly or dashboard
      if (data.jitsi_url) {
        urlToOpen = data.jitsi_url;
      } else {
        urlToOpen = `/?action=open_call&appointment_id=${data.appointment_id}`;
      }
      break;
    
    case 'emergency_appointment':
    case 'new_appointment':
    case 'appointment_created':
      // Open appointment details
      urlToOpen = `/?action=view_appointment&appointment_id=${data.appointment_id}`;
      break;
    
    case 'new_note':
    case 'doctor_note':
    case 'provider_note':
      // Open appointment with notes
      urlToOpen = `/?action=view_notes&appointment_id=${data.appointment_id}`;
      break;
    
    default:
      urlToOpen = '/';
  }

  console.log('🌐 [Service Worker] Opening URL:', urlToOpen);

  // Open or focus the app
  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true })
      .then((clientList) => {
        // Check if app is already open
        for (let client of clientList) {
          if (client.url.includes(self.registration.scope) && 'focus' in client) {
            console.log('✅ [Service Worker] Focusing existing window');
            return client.focus().then(client => {
              // Send message to open app to handle the action
              client.postMessage({
                type: 'NOTIFICATION_CLICK',
                data: data
              });
              return client;
            });
          }
        }
        
        // App not open, open new window
        console.log('🆕 [Service Worker] Opening new window');
        if (clients.openWindow) {
          return clients.openWindow(urlToOpen);
        }
      })
  );
});

console.log('✅ [Service Worker] Firebase Cloud Messaging service worker loaded');
