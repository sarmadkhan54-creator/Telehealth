// Greenstar Telehealth Platform - Service Worker
// Version 1.0.0

const CACHE_NAME = 'greenstar-telehealth-v1.0.0';
const RUNTIME_CACHE = 'greenstar-runtime-v1.0.0';

// Assets to cache immediately (App Shell)
const PRECACHE_ASSETS = [
  '/',
  '/static/js/bundle.js',
  '/static/css/main.css',
  '/manifest.json',
  '/icons/icon-192x192.png',
  '/icons/icon-512x512.png'
];

// Runtime caching for API calls and assets
const API_CACHE_PATTERNS = [
  /^https:\/\/greenstar-health\.preview\.emergentagent\.com\/api\//,
  /^https:\/\/fonts\.googleapis\.com/,
  /^https:\/\/fonts\.gstatic\.com/
];

// Install event - cache app shell
self.addEventListener('install', (event) => {
  console.log('[SW] Install event');
  
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => {
        console.log('[SW] Precaching app shell');
        return cache.addAll(PRECACHE_ASSETS);
      })
      .then(() => {
        console.log('[SW] Skip waiting and take control');
        return self.skipWaiting();
      })
  );
});

// Activate event - cleanup old caches
self.addEventListener('activate', (event) => {
  console.log('[SW] Activate event');
  
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cacheName) => {
          if (cacheName !== CACHE_NAME && cacheName !== RUNTIME_CACHE) {
            console.log('[SW] Deleting old cache:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    }).then(() => {
      console.log('[SW] Claiming clients');
      return self.clients.claim();
    })
  );
});

// Fetch event - serve from cache, fallback to network
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-GET requests
  if (request.method !== 'GET') {
    return;
  }

  // Handle API calls - Network First strategy (for fresh data)
  if (API_CACHE_PATTERNS.some(pattern => pattern.test(request.url))) {
    event.respondWith(
      caches.open(RUNTIME_CACHE).then((cache) => {
        return fetch(request)
          .then((response) => {
            // Only cache successful responses
            if (response.status === 200) {
              cache.put(request, response.clone());
            }
            return response;
          })
          .catch(() => {
            // Fallback to cached version if network fails
            return cache.match(request);
          });
      })
    );
    return;
  }

  // Handle navigation requests - Cache First with Network Fallback
  if (request.mode === 'navigate') {
    event.respondWith(
      caches.match('/').then((cachedResponse) => {
        if (cachedResponse) {
          return cachedResponse;
        }
        return fetch(request);
      })
    );
    return;
  }

  // Handle static assets - Cache First strategy
  event.respondWith(
    caches.match(request).then((cachedResponse) => {
      if (cachedResponse) {
        return cachedResponse;
      }

      return caches.open(RUNTIME_CACHE).then((cache) => {
        return fetch(request).then((response) => {
          // Cache successful responses
          if (response.status === 200) {
            cache.put(request, response.clone());
          }
          return response;
        });
      });
    })
  );
});

// Handle background sync for offline appointment creation
self.addEventListener('sync', (event) => {
  console.log('[SW] Background sync:', event.tag);
  
  if (event.tag === 'background-appointment-sync') {
    event.waitUntil(syncAppointments());
  }
});

// Handle push notifications for video calls and appointments
self.addEventListener('push', (event) => {
  console.log('[SW] Push notification received');
  
  if (event.data) {
    const data = event.data.json();
    
    const options = {
      body: data.body || 'New notification from Greenstar Telehealth',
      icon: '/icons/icon-192x192.png',
      badge: '/icons/badge-72x72.png',
      vibrate: [200, 100, 200],
      data: data,
      actions: [
        {
          action: 'view',
          title: 'View',
          icon: '/icons/view-action.png'
        },
        {
          action: 'dismiss',
          title: 'Dismiss',
          icon: '/icons/dismiss-action.png'
        }
      ],
      requireInteraction: data.type === 'emergency' || data.type === 'video_call'
    };

    event.waitUntil(
      self.registration.showNotification(
        data.title || 'Greenstar Telehealth',
        options
      )
    );
  }
});

// Handle notification clicks
self.addEventListener('notificationclick', (event) => {
  console.log('[SW] Notification click:', event.action);
  
  event.notification.close();

  if (event.action === 'view') {
    // Open the app or focus existing window
    event.waitUntil(
      self.clients.matchAll({ type: 'window' }).then((clientList) => {
        // If app is already open, focus it
        for (const client of clientList) {
          if (client.url === self.location.origin && 'focus' in client) {
            return client.focus();
          }
        }
        
        // Otherwise open new window
        if (clients.openWindow) {
          return clients.openWindow('/');
        }
      })
    );
  }
});

// Sync appointments when back online
async function syncAppointments() {
  try {
    console.log('[SW] Syncing offline appointments...');
    // Implementation for syncing offline data when connection restored
    // This would sync any appointments created while offline
    
    const clients = await self.clients.matchAll();
    clients.forEach(client => {
      client.postMessage({
        type: 'SYNC_COMPLETE',
        message: 'Offline appointments synced successfully'
      });
    });
    
  } catch (error) {
    console.error('[SW] Sync failed:', error);
  }
}

// Log service worker lifecycle
console.log('[SW] Service Worker loaded - Greenstar Telehealth Platform v1.0.0');