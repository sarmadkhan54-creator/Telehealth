/**
 * Push Notifications Utility for Greenstar Telehealth PWA
 * Handles push notification subscription, permission requests, and service worker integration
 */

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Convert VAPID key from base64 to Uint8Array
function urlBase64ToUint8Array(base64String) {
  const padding = '='.repeat((4 - base64String.length % 4) % 4);
  const base64 = (base64String + padding)
    .replace(/\-/g, '+')
    .replace(/_/g, '/');

  const rawData = window.atob(base64);
  const outputArray = new Uint8Array(rawData.length);

  for (let i = 0; i < rawData.length; ++i) {
    outputArray[i] = rawData.charCodeAt(i);
  }
  return outputArray;
}

export class PushNotificationManager {
  constructor() {
    this.vapidPublicKey = null;
    this.subscription = null;
    this.isSupported = 'serviceWorker' in navigator && 'PushManager' in window;
  }

  // Check if push notifications are supported
  isSupported() {
    return 'serviceWorker' in navigator && 'PushManager' in window;
  }

  // Get current notification permission status
  getPermissionStatus() {
    if (!('Notification' in window)) {
      return 'unsupported';
    }
    return Notification.permission;
  }

  // Request notification permission from user
  async requestPermission() {
    if (!('Notification' in window)) {
      console.log('This browser does not support notifications');
      return 'unsupported';
    }

    try {
      const permission = await Notification.requestPermission();
      console.log('📱 Notification permission:', permission);
      return permission;
    } catch (error) {
      console.error('Error requesting notification permission:', error);
      return 'denied';
    }
  }

  // Get VAPID public key from backend
  async getVapidPublicKey() {
    try {
      const token = localStorage.getItem('authToken');
      const response = await fetch(`${API}/push/vapid-key`, {
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (!response.ok) {
        throw new Error('Failed to get VAPID key');
      }

      const data = await response.json();
      this.vapidPublicKey = data.vapid_public_key;
      return this.vapidPublicKey;
    } catch (error) {
      console.error('Error getting VAPID key:', error);
      throw error;
    }
  }

  // Subscribe to push notifications
  async subscribe() {
    try {
      // Check if already have permission
      const permission = await this.requestPermission();
      if (permission !== 'granted') {
        throw new Error('Notification permission not granted');
      }

      // Get service worker registration
      const registration = await navigator.serviceWorker.ready;
      
      // Get VAPID key
      if (!this.vapidPublicKey) {
        await this.getVapidPublicKey();
      }

      // Check if already subscribed
      const existingSubscription = await registration.pushManager.getSubscription();
      if (existingSubscription) {
        this.subscription = existingSubscription;
        console.log('✅ Already subscribed to push notifications');
        return existingSubscription;
      }

      // Create new subscription
      const subscription = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(this.vapidPublicKey)
      });

      this.subscription = subscription;

      // Send subscription to backend
      await this.sendSubscriptionToBackend(subscription);

      console.log('✅ Successfully subscribed to push notifications');
      return subscription;

    } catch (error) {
      console.error('❌ Error subscribing to push notifications:', error);
      throw error;
    }
  }

  // Send subscription to backend
  async sendSubscriptionToBackend(subscription) {
    try {
      const token = localStorage.getItem('authToken');
      
      const subscriptionData = {
        subscription: {
          endpoint: subscription.endpoint,
          keys: {
            p256dh: btoa(String.fromCharCode.apply(null, new Uint8Array(subscription.getKey('p256dh')))),
            auth: btoa(String.fromCharCode.apply(null, new Uint8Array(subscription.getKey('auth'))))
          }
        }
      };

      const response = await fetch(`${API}/push/subscribe`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(subscriptionData)
      });

      if (!response.ok) {
        throw new Error('Failed to send subscription to backend');
      }

      const result = await response.json();
      console.log('✅ Subscription sent to backend:', result);
      return result;

    } catch (error) {
      console.error('❌ Error sending subscription to backend:', error);
      throw error;
    }
  }

  // Unsubscribe from push notifications
  async unsubscribe() {
    try {
      const registration = await navigator.serviceWorker.ready;
      const subscription = await registration.pushManager.getSubscription();

      if (subscription) {
        await subscription.unsubscribe();
        console.log('✅ Unsubscribed from push notifications');
      }

      // Remove subscription from backend
      const token = localStorage.getItem('authToken');
      await fetch(`${API}/push/unsubscribe`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      this.subscription = null;
      console.log('✅ Removed subscription from backend');

    } catch (error) {
      console.error('❌ Error unsubscribing from push notifications:', error);
      throw error;
    }
  }

  // Send test notification
  async sendTestNotification() {
    try {
      const token = localStorage.getItem('authToken');
      const response = await fetch(`${API}/push/test`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
        }
      });

      if (!response.ok) {
        throw new Error('Failed to send test notification');
      }

      const result = await response.json();
      console.log('✅ Test notification sent:', result);
      return result;

    } catch (error) {
      console.error('❌ Error sending test notification:', error);
      throw error;
    }
  }

  // Check if user is currently subscribed
  async isSubscribed() {
    try {
      const registration = await navigator.serviceWorker.ready;
      const subscription = await registration.pushManager.getSubscription();
      return !!subscription;
    } catch (error) {
      console.error('Error checking subscription status:', error);
      return false;
    }
  }

  // Initialize push notifications after user login
  async initialize(autoSubscribe = true) {
    try {
      if (!this.isSupported()) {
        console.log('❌ Push notifications not supported');
        return false;
      }

      const permission = this.getPermissionStatus();
      console.log('📱 Current notification permission:', permission);

      if (permission === 'granted' && autoSubscribe) {
        await this.subscribe();
      } else if (permission === 'default') {
        console.log('📱 Push notifications available - user can subscribe manually');
      }

      return true;

    } catch (error) {
      console.error('❌ Error initializing push notifications:', error);
      return false;
    }
  }
}

// Export singleton instance
export const pushNotificationManager = new PushNotificationManager();

// Utility function to show browser notification (fallback)
export function showBrowserNotification(title, options = {}) {
  if ('Notification' in window && Notification.permission === 'granted') {
    const notification = new Notification(title, {
      icon: '/icons/icon-192x192.png',
      badge: '/icons/badge-72x72.png',
      ...options
    });

    notification.onclick = () => {
      window.focus();
      notification.close();
    };

    return notification;
  }
  console.log('Browser notifications not available');
  return null;
}