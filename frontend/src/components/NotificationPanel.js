import React, { useState, useEffect } from 'react';
import { X, Phone, PhoneOff, User, Clock, AlertTriangle, Check, Eye, Calendar, CheckCircle } from 'lucide-react';

const NotificationPanel = ({ user, isOpen, onClose }) => {
  const [notifications, setNotifications] = useState([]);
  const [activeTab, setActiveTab] = useState('all');
  const [ws, setWs] = useState(null);

  const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
  const API = `${BACKEND_URL}/api`;

  useEffect(() => {
    if (isOpen) {
      // Setup WebSocket for real-time notifications
      setupNotificationWebSocket();
      // Load existing notifications
      loadNotifications();
    }

    return () => {
      if (ws) {
        ws.close();
      }
    };
  }, [isOpen, user.id]);

  const setupNotificationWebSocket = () => {
    try {
      let wsUrl;
      if (BACKEND_URL.startsWith('https://')) {
        wsUrl = BACKEND_URL.replace('https://', 'wss://') + `/api/ws/${user.id}`;
      } else if (BACKEND_URL.startsWith('http://')) {
        wsUrl = BACKEND_URL.replace('http://', 'ws://') + `/api/ws/${user.id}`;
      } else {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        wsUrl = `${protocol}//${window.location.host}/api/ws/${user.id}`;
      }

      console.log(`🔔 Connecting to notification WebSocket: ${wsUrl}`);

      const websocket = new WebSocket(wsUrl);
      
      websocket.onopen = () => {
        console.log('✅ Notification WebSocket connected');
        setWs(websocket);
      };

      websocket.onmessage = (event) => {
        try {
          const notification = JSON.parse(event.data);
          console.log('📨 Received notification:', notification);
          
          // Validate notification data with safe defaults
          if (!notification || typeof notification !== 'object') {
            console.warn('Invalid notification received:', notification);
            return;
          }
          
          // Add notification to the panel with comprehensive safe defaults
          const newNotification = {
            id: Date.now() + Math.random(), // Ensure unique ID
            type: (notification.type && typeof notification.type === 'string') ? notification.type : 'unknown',
            title: getNotificationTitle(notification) || 'New Notification',
            message: getNotificationMessage(notification) || 'You have a new notification',
            timestamp: new Date(),
            data: (notification && typeof notification === 'object') ? notification : {},
            isRead: false,
            priority: notification.type === 'emergency_appointment' ? 'high' : 
                     notification.type === 'jitsi_call_invitation' ? 'urgent' : 'normal'
          };

          setNotifications(prev => {
            try {
              // Ensure prev is always an array
              const prevArray = Array.isArray(prev) ? prev : [];
              const updatedNotifications = [newNotification, ...prevArray];
              
              // Limit to 50 notifications to prevent memory issues
              const limitedNotifications = updatedNotifications.slice(0, 50);
              
              // Save to localStorage with error handling
              try {
                saveNotifications(limitedNotifications);
              } catch (saveError) {
                console.error('Error saving notifications:', saveError);
              }
              
              return limitedNotifications;
            } catch (error) {
              console.error('Error updating notifications state:', error);
              return Array.isArray(prev) ? prev : [];
            }
          });

          // Show browser notification if permission granted and supported
          try {
            if (typeof Notification !== 'undefined' && 
                Notification.permission === 'granted' && 
                newNotification.title && 
                newNotification.message) {
              
              const browserNotification = new Notification(newNotification.title, {
                body: newNotification.message.substring(0, 100), // Limit body length
                icon: '/icons/icon-192x192.png',
                badge: '/icons/badge-72x72.png',
                tag: notification.type || 'default',
                requireInteraction: notification.type === 'jitsi_call_invitation'
              });

              browserNotification.onclick = () => {
                try {
                  handleNotificationClick(newNotification);
                  browserNotification.close();
                } catch (error) {
                  console.error('Error handling notification click:', error);
                }
              };
              
              // Auto-close notification after 10 seconds
              setTimeout(() => {
                try {
                  browserNotification.close();
                } catch (error) {
                  console.error('Error closing notification:', error);
                }
              }, 10000);
            }
          } catch (error) {
            console.error('Error creating browser notification:', error);
          }

          // Play notification sound for urgent notifications
          try {
            if (notification.type === 'jitsi_call_invitation' || notification.type === 'emergency_appointment') {
              playNotificationSound();
            }
          } catch (error) {
            console.error('Error playing notification sound:', error);
          }

        } catch (error) {
          console.error('Error processing notification:', error);
        }
      };

      websocket.onerror = (error) => {
        console.error('❌ Notification WebSocket error:', error);
      };

      websocket.onclose = () => {
        console.log('🔌 Notification WebSocket disconnected, attempting to reconnect...');
        setTimeout(() => {
          try {
            setupNotificationWebSocket();
          } catch (error) {
            console.error('Error reconnecting WebSocket:', error);
          }
        }, 5000);
      };

    } catch (error) {
      console.error('❌ Error setting up notification WebSocket:', error);
      setTimeout(() => {
        try {
          setupNotificationWebSocket();
        } catch (retryError) {
          console.error('Error retrying WebSocket setup:', retryError);
        }
      }, 5000);
    }
  };

  const loadNotifications = () => {
    try {
      const savedNotifications = localStorage.getItem(`notifications_${user.id}`);
      if (savedNotifications) {
        const parsed = JSON.parse(savedNotifications);
        
        // Validate and clean the loaded data
        if (Array.isArray(parsed)) {
          const validNotifications = parsed
            .filter(n => n && typeof n === 'object' && n.id && n.type) // Only valid notifications
            .map(n => ({
              ...n,
              timestamp: new Date(n.timestamp) // Convert timestamp back to Date object
            }))
            .slice(0, 50); // Limit to 50 notifications
          
          setNotifications(validNotifications);
        } else {
          console.warn('Invalid notifications data in localStorage');
          setNotifications([]);
        }
      } else {
        setNotifications([]);
      }
    } catch (error) {
      console.error('Error loading saved notifications:', error);
      setNotifications([]);
      // Clear corrupted data
      try {
        localStorage.removeItem(`notifications_${user.id}`);
      } catch (clearError) {
        console.error('Error clearing corrupted notifications:', clearError);
      }
    }
  };

  const saveNotifications = (notifications) => {
    try {
      if (!Array.isArray(notifications)) {
        console.warn('Invalid notifications array for saving:', notifications);
        return;
      }
      
      // Limit storage size and clean up old notifications
      const notificationsToSave = notifications
        .slice(0, 50) // Keep only latest 50
        .map(n => ({
          ...n,
          timestamp: n.timestamp instanceof Date ? n.timestamp.toISOString() : n.timestamp
        }));
      
      const storageKey = `notifications_${user.id}`;
      localStorage.setItem(storageKey, JSON.stringify(notificationsToSave));
    } catch (error) {
      console.error('Error saving notifications to localStorage:', error);
      // Clear corrupted data
      try {
        localStorage.removeItem(`notifications_${user.id}`);
      } catch (clearError) {
        console.error('Error clearing corrupted notifications:', clearError);
      }
    }
  };

  const getNotificationTitle = (notification) => {
    switch (notification.type) {
      case 'jitsi_call_invitation':
        return `📞 Incoming Video Call`;
      case 'emergency_appointment':
        return `🚨 Emergency Appointment`;
      case 'new_appointment':
        return `📅 New Appointment`;
      case 'appointment_accepted':
        return `✅ Appointment Accepted`;
      case 'appointment_updated':
        return `📝 Appointment Updated`;
      case 'video_call_invitation':
        return `📞 Video Call Invitation`;
      default:
        return '📨 New Notification';
    }
  };

  const getNotificationMessage = (notification) => {
    switch (notification.type) {
      case 'jitsi_call_invitation':
        return `${notification.caller} is calling you for ${notification.patient?.name || 'patient consultation'}`;
      case 'emergency_appointment':
        return `Emergency consultation for ${notification.patient_name} from ${notification.provider_name}`;
      case 'new_appointment':
        return `New consultation for ${notification.patient_name} from ${notification.provider_name}`;
      case 'appointment_accepted':
        return `Dr. ${notification.doctor_name} accepted your appointment for ${notification.patient_name}`;
      case 'appointment_updated':
        return `Appointment for ${notification.patient_name} was updated by ${notification.updated_by}`;
      case 'video_call_invitation':
        return `${notification.caller} is inviting you to a video consultation`;
      default:
        return 'New notification received';
    }
  };

  const playNotificationSound = () => {
    try {
      // Create notification sound
      const audioContext = new (window.AudioContext || window.webkitAudioContext)();
      const oscillator = audioContext.createOscillator();
      const gainNode = audioContext.createGain();

      oscillator.connect(gainNode);
      gainNode.connect(audioContext.destination);

      oscillator.type = 'sine';
      oscillator.frequency.setValueAtTime(800, audioContext.currentTime);
      gainNode.gain.setValueAtTime(0.1, audioContext.currentTime);
      gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.5);

      oscillator.start(audioContext.currentTime);
      oscillator.stop(audioContext.currentTime + 0.5);
    } catch (error) {
      console.error('Error playing notification sound:', error);
    }
  };

  const handleNotificationClick = (notification) => {
    switch (notification.type) {
      case 'jitsi_call_invitation':
        // Answer the call
        if (notification.data.jitsi_url) {
          window.open(notification.data.jitsi_url, '_blank', 'width=1200,height=800');
        }
        break;
      case 'emergency_appointment':
        // Open appointment details
        if (notification.data.appointment_id) {
          // You can trigger opening appointment modal here
          console.log('Opening appointment:', notification.data.appointment_id);
        }
        break;
      default:
        console.log('Notification clicked:', notification);
    }

    // Mark as read
    markAsRead(notification.id);
  };

  const markAsRead = (notificationId) => {
    setNotifications(prev => {
      const updated = prev.map(n => 
        n.id === notificationId ? { ...n, isRead: true } : n
      );
      saveNotifications(updated);
      return updated;
    });
  };

  const markAllAsRead = () => {
    setNotifications(prev => {
      const updated = prev.map(n => ({ ...n, isRead: true }));
      saveNotifications(updated);
      return updated;
    });
  };

  const clearNotifications = () => {
    setNotifications([]);
    localStorage.removeItem(`notifications_${user.id}`);
  };

  // Accept functionality removed - doctors can now directly video call from dashboard

  const startVideoCall = async (appointmentId) => {
    try {
      const response = await fetch(`${API}/video-call/session/${appointmentId}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('authToken')}`
        }
      });
      
      if (response.ok) {
        const data = await response.json();
        const configuredJitsiUrl = `${data.jitsi_url}#config.startWithAudioMuted=false&config.startWithVideoMuted=false&config.requireDisplayName=false&config.enableWelcomePage=false&config.prejoinPageEnabled=false&config.enableModeratedDiscussion=false&config.disableModeratorIndicator=true&userInfo.displayName=${user.full_name}`;
        
        // Open video call
        if (/Android|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent)) {
          window.location.href = configuredJitsiUrl;
        } else {
          const newWindow = window.open(configuredJitsiUrl, '_blank', 'width=1200,height=800');
          if (!newWindow || newWindow.closed || typeof newWindow.closed == 'undefined') {
            window.location.href = configuredJitsiUrl;
          }
        }
      }
    } catch (error) {
      console.error('Error starting video call:', error);
      alert('Error starting video call. Please try again.');
    }
  };

  const filteredNotifications = notifications.filter(notification => {
    switch (activeTab) {
      case 'calls':
        return notification.type === 'jitsi_call_invitation' || notification.type === 'video_call_invitation';
      case 'appointments':
        return notification.type === 'emergency_appointment' || notification.type === 'new_appointment' || notification.type === 'appointment_accepted' || notification.type === 'appointment_updated';
      case 'unread':
        return !notification.isRead;
      default:
        return true;
    }
  });

  const unreadCount = notifications.filter(n => !n.isRead).length;

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-2xl w-full max-w-2xl h-4/5 flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200">
          <div className="flex items-center space-x-3">
            <h2 className="text-xl font-bold text-gray-900">Notifications</h2>
            {unreadCount > 0 && (
              <span className="bg-red-500 text-white text-xs font-bold px-2 py-1 rounded-full">
                {unreadCount}
              </span>
            )}
          </div>
          <div className="flex items-center space-x-2">
            <button
              onClick={markAllAsRead}
              className="text-sm text-blue-600 hover:text-blue-800"
            >
              Mark all read
            </button>
            <button
              onClick={clearNotifications}
              className="text-sm text-red-600 hover:text-red-800"
            >
              Clear all
            </button>
            <button
              onClick={onClose}
              className="text-gray-500 hover:text-gray-700"
            >
              <X className="w-6 h-6" />
            </button>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-gray-200">
          {[
            { key: 'all', label: 'All', icon: null },
            { key: 'calls', label: 'Calls', icon: Phone },
            { key: 'appointments', label: 'Appointments', icon: Calendar },
            { key: 'unread', label: 'Unread', icon: Eye }
          ].map(tab => {
            const Icon = tab.icon;
            const count = filteredNotifications.length;
            return (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={`flex-1 flex items-center justify-center space-x-2 py-3 px-4 text-sm font-medium border-b-2 transition-colors ${
                  activeTab === tab.key
                    ? 'border-green-500 text-green-600 bg-green-50'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:bg-gray-50'
                }`}
              >
                {Icon && <Icon className="w-4 h-4" />}
                <span>{tab.label}</span>
                {tab.key === activeTab && count > 0 && (
                  <span className="ml-1 text-xs">({count})</span>
                )}
              </button>
            );
          })}
        </div>

        {/* Notifications List */}
        <div className="flex-1 overflow-y-auto">
          {filteredNotifications.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-gray-500">
              <div className="text-6xl mb-4">🔔</div>
              <p className="text-lg font-medium">No notifications</p>
              <p className="text-sm">You're all caught up!</p>
            </div>
          ) : (
            <div className="divide-y divide-gray-200">
              {filteredNotifications.map((notification) => (
                <div
                  key={notification.id}
                  className={`p-4 hover:bg-gray-50 transition-colors cursor-pointer ${
                    !notification.isRead ? 'bg-blue-50 border-l-4 border-l-blue-500' : ''
                  } ${
                    notification.priority === 'urgent' ? 'bg-red-50 border-l-4 border-l-red-500' : ''
                  }`}
                  onClick={() => handleNotificationClick(notification)}
                >
                  <div className="flex items-start space-x-3">
                    <div className={`flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center ${
                      notification.priority === 'urgent' ? 'bg-red-100' :
                      notification.priority === 'high' ? 'bg-orange-100' : 'bg-green-100'
                    }`}>
                      {notification.type === 'jitsi_call_invitation' || notification.type === 'video_call_invitation' ? (
                        <Phone className={`w-5 h-5 ${
                          notification.priority === 'urgent' ? 'text-red-600' : 'text-green-600'
                        }`} />
                      ) : notification.type === 'emergency_appointment' ? (
                        <AlertTriangle className="w-5 h-5 text-red-600" />
                      ) : (
                        <User className="w-5 h-5 text-green-600" />
                      )}
                    </div>

                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between">
                        <p className="text-sm font-semibold text-gray-900 truncate">
                          {notification.title}
                        </p>
                        <div className="flex items-center space-x-2">
                          <span className="text-xs text-gray-500">
                            {notification.timestamp.toLocaleTimeString([], { 
                              hour: '2-digit', 
                              minute: '2-digit' 
                            })}
                          </span>
                          {!notification.isRead && (
                            <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                          )}
                        </div>
                      </div>
                      
                      <p className="text-sm text-gray-600 mt-1">
                        {notification.message}
                      </p>

                      {/* Action Buttons for Video Call Invitations */}
                      {(notification.type === 'jitsi_call_invitation' || notification.type === 'video_call_invitation') && (
                        <div className="flex items-center space-x-2 mt-3">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              if (notification.data.jitsi_url) {
                                window.open(notification.data.jitsi_url, '_blank', 'width=1200,height=800');
                              } else if (notification.data.appointment_id) {
                                startVideoCall(notification.data.appointment_id);
                              }
                              markAsRead(notification.id);
                            }}
                            className="flex items-center space-x-1 px-3 py-1 bg-green-500 text-white text-xs rounded-full hover:bg-green-600 transition-colors"
                          >
                            <Phone className="w-3 h-3" />
                            <span>Join Call</span>
                          </button>
                          
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              markAsRead(notification.id);
                            }}
                            className="flex items-center space-x-1 px-3 py-1 bg-red-500 text-white text-xs rounded-full hover:bg-red-600 transition-colors"
                          >
                            <PhoneOff className="w-3 h-3" />
                            <span>Decline</span>
                          </button>
                          
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              if (notification.data.appointment_id) {
                                startVideoCall(notification.data.appointment_id);
                              }
                              markAsRead(notification.id);
                            }}
                            className="flex items-center space-x-1 px-3 py-1 bg-blue-500 text-white text-xs rounded-full hover:bg-blue-600 transition-colors"
                          >
                            <Phone className="w-3 h-3" />
                            <span>Call Back</span>
                          </button>
                        </div>
                      )}

                      {/* Action Buttons for Appointments */}
                      {(notification.type === 'emergency_appointment' || notification.type === 'new_appointment') && notification.data.appointment_id && (
                        <div className="flex items-center space-x-2 mt-3">
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              startVideoCall(notification.data.appointment_id);
                              markAsRead(notification.id);
                            }}
                            className="flex items-center space-x-1 px-3 py-1 bg-green-500 text-white text-xs rounded-full hover:bg-green-600 transition-colors"
                          >
                            <Phone className="w-3 h-3" />
                            <span>Call Provider</span>
                          </button>
                        </div>
                      )}

                      {/* Patient Info for Appointments */}
                      {(notification.type === 'emergency_appointment' || notification.type === 'new_appointment') && notification.data.patient && (
                        <div className={`mt-3 p-2 rounded-lg ${
                          notification.type === 'emergency_appointment' ? 'bg-red-50' : 'bg-blue-50'
                        }`}>
                          <p className={`text-xs font-medium ${
                            notification.type === 'emergency_appointment' ? 'text-red-800' : 'text-blue-800'
                          }`}>
                            Patient: {notification.data.patient.name} ({notification.data.patient.age}y, {notification.data.patient.gender})
                          </p>
                          <p className={`text-xs ${
                            notification.type === 'emergency_appointment' ? 'text-red-700' : 'text-blue-700'
                          }`}>
                            Reason: {notification.data.patient.consultation_reason}
                          </p>
                          {notification.data.provider_name && (
                            <p className={`text-xs ${
                              notification.type === 'emergency_appointment' ? 'text-red-600' : 'text-blue-600'
                            }`}>
                              Provider: {notification.data.provider_name} ({notification.data.provider_district})
                            </p>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default NotificationPanel;