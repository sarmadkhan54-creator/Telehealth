import React, { useState, useEffect } from 'react';
import { pushNotificationManager } from '../utils/pushNotifications';

const NotificationSettings = ({ isOpen, onClose }) => {
  const [notificationStatus, setNotificationStatus] = useState('checking');
  const [isSubscribed, setIsSubscribed] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (isOpen) {
      checkNotificationStatus();
    }
  }, [isOpen]);

  const checkNotificationStatus = async () => {
    try {
      setNotificationStatus('checking');
      
      if (!pushNotificationManager.isSupported()) {
        setNotificationStatus('unsupported');
        return;
      }

      const permission = pushNotificationManager.getPermissionStatus();
      const subscribed = await pushNotificationManager.isSubscribed();
      
      setNotificationStatus(permission);
      setIsSubscribed(subscribed);
    } catch (error) {
      console.error('Error checking notification status:', error);
      setNotificationStatus('error');
    }
  };

  const handleEnableNotifications = async () => {
    setLoading(true);
    try {
      await pushNotificationManager.subscribe();
      await checkNotificationStatus();
      
      // Show success message
      alert('✅ Push notifications enabled successfully!');
    } catch (error) {
      console.error('Error enabling notifications:', error);
      alert('❌ Failed to enable push notifications. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleDisableNotifications = async () => {
    setLoading(true);
    try {
      await pushNotificationManager.unsubscribe();
      await checkNotificationStatus();
      
      // Show success message
      alert('✅ Push notifications disabled successfully!');
    } catch (error) {
      console.error('Error disabling notifications:', error);
      alert('❌ Failed to disable push notifications. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleTestNotification = async () => {
    setLoading(true);
    try {
      const result = await pushNotificationManager.sendTestNotification();
      if (result.success) {
        alert('✅ Test notification sent! Check your notifications.');
      } else {
        alert('⚠️ Test notification failed. Make sure notifications are enabled.');
      }
    } catch (error) {
      console.error('Error sending test notification:', error);
      alert('❌ Failed to send test notification.');
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  const getStatusIcon = () => {
    switch (notificationStatus) {
      case 'granted':
        return '✅';
      case 'denied':
        return '❌';
      case 'default':
        return '⚠️';
      case 'unsupported':
        return '🚫';
      case 'checking':
        return '🔄';
      default:
        return '❓';
    }
  };

  const getStatusText = () => {
    switch (notificationStatus) {
      case 'granted':
        return isSubscribed ? 'Enabled and Active' : 'Permission Granted';
      case 'denied':
        return 'Blocked by Browser';
      case 'default':
        return 'Not Configured';
      case 'unsupported':
        return 'Not Supported';
      case 'checking':
        return 'Checking...';
      default:
        return 'Unknown Status';
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-md w-full mx-4">
        <div className="p-6">
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-xl font-bold text-gray-900">
              🔔 Notification Settings
            </h2>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 transition-colors"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <div className="space-y-6">
            {/* Status Section */}
            <div className="bg-gray-50 rounded-lg p-4">
              <h3 className="font-medium text-gray-900 mb-2">Current Status</h3>
              <div className="flex items-center space-x-2">
                <span className="text-2xl">{getStatusIcon()}</span>
                <span className="text-sm text-gray-600">{getStatusText()}</span>
              </div>
            </div>

            {/* Notification Types */}
            <div>
              <h3 className="font-medium text-gray-900 mb-3">You'll receive notifications for:</h3>
              <ul className="space-y-2 text-sm text-gray-600">
                <li className="flex items-center space-x-2">
                  <span>📞</span>
                  <span>Incoming video call invitations</span>
                </li>
                <li className="flex items-center space-x-2">
                  <span>⏰</span>
                  <span>Appointment reminders</span>
                </li>
                <li className="flex items-center space-x-2">
                  <span>🚨</span>
                  <span>Emergency appointment alerts</span>
                </li>
                <li className="flex items-center space-x-2">
                  <span>📋</span>
                  <span>Appointment status updates</span>
                </li>
              </ul>
            </div>

            {/* Action Buttons */}
            <div className="space-y-3">
              {notificationStatus === 'unsupported' ? (
                <div className="text-center py-4">
                  <p className="text-sm text-gray-500">
                    Push notifications are not supported on this device.
                  </p>
                </div>
              ) : notificationStatus === 'denied' ? (
                <div className="text-center py-4">
                  <p className="text-sm text-gray-500 mb-2">
                    Notifications are blocked. Please enable them in your browser settings.
                  </p>
                  <button
                    onClick={checkNotificationStatus}
                    disabled={loading}
                    className="text-blue-600 hover:text-blue-700 text-sm font-medium"
                  >
                    Check Again
                  </button>
                </div>
              ) : (
                <>
                  {!isSubscribed ? (
                    <button
                      onClick={handleEnableNotifications}
                      disabled={loading}
                      className="w-full bg-green-600 text-white py-2 px-4 rounded-lg hover:bg-green-700 transition-colors disabled:opacity-50"
                    >
                      {loading ? '🔄 Enabling...' : '🔔 Enable Notifications'}
                    </button>
                  ) : (
                    <div className="space-y-2">
                      <button
                        onClick={handleTestNotification}
                        disabled={loading}
                        className="w-full bg-blue-600 text-white py-2 px-4 rounded-lg hover:bg-blue-700 transition-colors disabled:opacity-50"
                      >
                        {loading ? '🔄 Sending...' : '🧪 Send Test Notification'}
                      </button>
                      
                      <button
                        onClick={handleDisableNotifications}
                        disabled={loading}
                        className="w-full bg-red-600 text-white py-2 px-4 rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50"
                      >
                        {loading ? '🔄 Disabling...' : '🔕 Disable Notifications'}
                      </button>
                    </div>
                  )}
                </>
              )}
            </div>

            {/* Help Text */}
            <div className="bg-blue-50 rounded-lg p-3">
              <h4 className="font-medium text-blue-900 mb-1">💡 Tips</h4>
              <ul className="text-xs text-blue-700 space-y-1">
                <li>• Install this app on your home screen for the best experience</li>
                <li>• Notifications work even when the app is closed</li>
                <li>• You can change these settings anytime</li>
              </ul>
            </div>
          </div>

          <div className="mt-6 pt-4 border-t border-gray-200">
            <button
              onClick={onClose}
              className="w-full bg-gray-100 text-gray-700 py-2 px-4 rounded-lg hover:bg-gray-200 transition-colors"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default NotificationSettings;