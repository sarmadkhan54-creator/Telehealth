import React, { useState, useEffect } from 'react';
import { X, Phone, PhoneOff, User, Clock, AlertTriangle, Check, Eye, Calendar, CheckCircle, Bell } from 'lucide-react';
import axios from 'axios';

const NotificationPanel = ({ user, isOpen, onClose }) => {
  const [notifications, setNotifications] = useState([]);
  const [activeTab, setActiveTab] = useState('all');
  const [ws, setWs] = useState(null);
  const [selectedNotificationAppointment, setSelectedNotificationAppointment] = useState(null);
  const [showAppointmentDetailsModal, setShowAppointmentDetailsModal] = useState(false);

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

  const getNotificationIcon = (type) => {
    switch (type) {
      case 'emergency_appointment':
      case 'new_appointment_created':
        return '🚨';
      case 'new_appointment':
        return '📅';
      case 'jitsi_call_invitation':
      case 'video_call_invitation':
        return '📞';
      default:
        return '📨';
    }
  };

  const formatDateTime = (timestamp) => {
    if (!timestamp) return '';
    const date = new Date(timestamp);
    return date.toLocaleString();
  };

  const handleNotificationClick = (notification) => {
    console.log('🔔 Notification clicked:', notification);
    
    switch (notification.type) {
      case 'jitsi_call_invitation':
      case 'video_call_invitation':
      case 'incoming_video_call':
        // Handle video call invitation
        if (notification.jitsi_url) {
          window.open(notification.jitsi_url, '_blank');
        }
        markAsRead(notification.id);
        break;
        
      case 'new_appointment_created':
      case 'emergency_appointment':
      case 'new_appointment':
        // Navigate to appointment details
        if (notification.appointment) {
          setSelectedNotificationAppointment(notification.appointment);
          setShowAppointmentDetailsModal(true);
        } else if (notification.appointment_id) {
          // Fetch appointment details and show modal
          fetchAppointmentDetails(notification.appointment_id);
        }
        markAsRead(notification.id);
        break;
        
      case 'new_note':
      case 'doctor_note':
      case 'provider_note':
        // Navigate to appointment with note focus
        if (notification.appointment_id) {
          fetchAppointmentDetails(notification.appointment_id, 'notes');
        }
        markAsRead(notification.id);
        break;
        
      case 'user_deleted':
      case 'appointment_cancelled':
        // Show acknowledgment and refresh
        alert(`${notification.message} - Data will be refreshed`);
        if (typeof window.location.reload === 'function') {
          setTimeout(() => window.location.reload(), 1000);
        }
        markAsRead(notification.id);
        break;
        
      default:
        // Generic notification - show details if available
        if (notification.appointment || notification.appointment_id) {
          if (notification.appointment) {
            setSelectedNotificationAppointment(notification.appointment);
            setShowAppointmentDetailsModal(true);
          } else {
            fetchAppointmentDetails(notification.appointment_id);
          }
        }
        markAsRead(notification.id);
    }
  };

  const fetchAppointmentDetails = async (appointmentId, focusTab = 'details') => {
    try {
      console.log('📋 Fetching appointment details for:', appointmentId);
      const response = await axios.get(`${API}/appointments/${appointmentId}`);
      if (response.data) {
        setSelectedNotificationAppointment(response.data);
        setShowAppointmentDetailsModal(true);
      }
    } catch (error) {
      console.error('❌ Error fetching appointment details:', error);
      alert('❌ Could not load appointment details. Please try again.');
    }
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
        
        // Universal video call opening - works on all devices consistently
        try {
          const newWindow = window.open(configuredJitsiUrl, '_blank', 'width=1200,height=800,scrollbars=yes,resizable=yes');
          if (newWindow) {
            newWindow.focus();
            console.log('✅ Video call opened from notification');
          } else {
            // Fallback for popup blockers
            console.log('⚠️ Popup blocked, using location.href fallback');
            window.location.href = configuredJitsiUrl;
          }
        } catch (error) {
          console.error('❌ Error opening video call, using fallback:', error);
          window.location.href = configuredJitsiUrl;
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
            <div className="text-center py-8">
              <Bell className="w-16 h-16 text-gray-300 mx-auto mb-4" />
              <p className="text-gray-500">No notifications</p>
            </div>
          ) : (
            <div className="space-y-3">
              {filteredNotifications.map((notification, index) => (
                <div 
                  key={index}
                  className={`p-4 rounded-lg border-l-4 cursor-pointer hover:bg-gray-100 transition-colors ${
                    notification.type === 'emergency_appointment' || notification.type === 'new_appointment_created' && notification.appointment?.appointment_type === 'emergency' ? 'border-red-500 bg-red-50' : 
                    notification.type === 'new_appointment' || notification.type === 'new_appointment_created' ? 'border-blue-500 bg-blue-50' :
                    'border-gray-300 bg-gray-50'
                  }`}
                  onClick={() => handleNotificationClick(notification)}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <p className="font-medium text-gray-900">
                        {getNotificationIcon(notification.type)} {notification.message}
                      </p>
                      
                      {/* FULL APPOINTMENT DETAILS IN NOTIFICATION */}
                      {notification.appointment && (
                        <div className="mt-3 p-3 bg-white rounded-lg border">
                          <div className="grid grid-cols-2 gap-2 text-sm">
                            <div>
                              <span className="font-medium text-gray-600">Patient:</span> {notification.appointment.patient?.name}
                            </div>
                            <div>
                              <span className="font-medium text-gray-600">Age:</span> {notification.appointment.patient?.age}
                            </div>
                            <div>
                              <span className="font-medium text-gray-600">Type:</span> 
                              <span className={`ml-1 px-2 py-1 rounded text-xs ${
                                notification.appointment.appointment_type === 'emergency' 
                                  ? 'bg-red-100 text-red-800' 
                                  : 'bg-blue-100 text-blue-800'
                              }`}>
                                {notification.appointment.appointment_type?.toUpperCase()}
                              </span>
                            </div>
                            <div>
                              <span className="font-medium text-gray-600">Provider:</span> {notification.appointment.provider_name}
                            </div>
                          </div>
                          
                          <div className="mt-2">
                            <span className="font-medium text-gray-600">Area:</span> {notification.appointment.patient?.area_of_consultation}
                          </div>
                          
                          {notification.appointment.patient?.history && (
                            <div className="mt-2">
                              <span className="font-medium text-gray-600">History:</span>
                              <p className="text-gray-800 text-sm mt-1">{notification.appointment.patient.history}</p>
                            </div>
                          )}
                          
                          {/* Vitals Display */}
                          {notification.appointment.patient?.vitals && (
                            <div className="mt-3">
                              <span className="font-medium text-gray-600">Vitals:</span>
                              <div className="grid grid-cols-2 gap-1 mt-1 text-xs">
                                {notification.appointment.patient.vitals.blood_pressure && (
                                  <div>BP: {notification.appointment.patient.vitals.blood_pressure}</div>
                                )}
                                {notification.appointment.patient.vitals.heart_rate && (
                                  <div>HR: {notification.appointment.patient.vitals.heart_rate}</div>
                                )}
                                {notification.appointment.patient.vitals.temperature && (
                                  <div>Temp: {notification.appointment.patient.vitals.temperature}°F</div>
                                )}
                                {notification.appointment.patient.vitals.hb && (
                                  <div>Hb: {notification.appointment.patient.vitals.hb} g/dL</div>
                                )}
                              </div>
                            </div>
                          )}
                          
                          <div className="mt-3 pt-2 border-t">
                            <p className="text-xs text-gray-500">💡 Click to view full details and take action</p>
                          </div>
                        </div>
                      )}
                      
                      <p className="text-sm text-gray-600 mt-2">
                        {formatDateTime(notification.timestamp)}
                      </p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

      {/* Appointment Details Modal from Notification */}
      {showAppointmentDetailsModal && selectedNotificationAppointment && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-xl font-bold text-gray-900">
                  📋 Appointment Details
                </h2>
                <button
                  onClick={() => setShowAppointmentDetailsModal(false)}
                  className="text-gray-400 hover:text-gray-600"
                >
                  <X className="w-6 h-6" />
                </button>
              </div>

              {/* Full Appointment Information */}
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-sm font-medium text-gray-600">Patient Name</label>
                    <p className="text-lg font-semibold">{selectedNotificationAppointment.patient?.name}</p>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-600">Age & Gender</label>
                    <p>{selectedNotificationAppointment.patient?.age} years, {selectedNotificationAppointment.patient?.gender}</p>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-sm font-medium text-gray-600">Appointment Type</label>
                    <span className={`inline-block px-3 py-1 rounded-full text-sm font-medium ${
                      selectedNotificationAppointment.appointment_type === 'emergency' 
                        ? 'bg-red-100 text-red-800' 
                        : 'bg-blue-100 text-blue-800'
                    }`}>
                      🚨 {selectedNotificationAppointment.appointment_type?.toUpperCase()}
                    </span>
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-600">Provider</label>
                    <p>{selectedNotificationAppointment.provider_name}</p>
                  </div>
                </div>

                <div>
                  <label className="text-sm font-medium text-gray-600">Area of Consultation</label>
                  <p className="font-medium">{selectedNotificationAppointment.patient?.area_of_consultation}</p>
                </div>

                <div>
                  <label className="text-sm font-medium text-gray-600">Patient History</label>
                  <p className="bg-gray-50 p-3 rounded-lg">{selectedNotificationAppointment.patient?.history}</p>
                </div>

                {/* Vitals Section */}
                {selectedNotificationAppointment.patient?.vitals && (
                  <div>
                    <label className="text-sm font-medium text-gray-600">Patient Vitals</label>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-2">
                      {selectedNotificationAppointment.patient.vitals.blood_pressure && (
                        <div className="bg-blue-50 p-2 rounded text-center">
                          <p className="text-xs text-blue-600">Blood Pressure</p>
                          <p className="font-semibold">{selectedNotificationAppointment.patient.vitals.blood_pressure}</p>
                        </div>
                      )}
                      {selectedNotificationAppointment.patient.vitals.heart_rate && (
                        <div className="bg-red-50 p-2 rounded text-center">
                          <p className="text-xs text-red-600">Heart Rate</p>
                          <p className="font-semibold">{selectedNotificationAppointment.patient.vitals.heart_rate} BPM</p>
                        </div>
                      )}
                      {selectedNotificationAppointment.patient.vitals.temperature && (
                        <div className="bg-orange-50 p-2 rounded text-center">
                          <p className="text-xs text-orange-600">Temperature</p>
                          <p className="font-semibold">{selectedNotificationAppointment.patient.vitals.temperature}°F</p>
                        </div>
                      )}
                      {selectedNotificationAppointment.patient.vitals.hb && (
                        <div className="bg-green-50 p-2 rounded text-center">
                          <p className="text-xs text-green-600">💉 Hemoglobin</p>
                          <p className="font-semibold">{selectedNotificationAppointment.patient.vitals.hb} g/dL</p>
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* Action Buttons */}
                <div className="flex space-x-3 pt-4 border-t">
                  {user.role === 'doctor' && (
                    <>
                      {selectedNotificationAppointment.appointment_type === 'emergency' ? (
                        <button
                          onClick={() => {
                            // Handle video call
                            console.log('Starting video call for:', selectedNotificationAppointment.id);
                            setShowAppointmentDetailsModal(false);
                          }}
                          className="flex-1 bg-red-600 text-white px-4 py-2 rounded-lg hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500"
                        >
                          🚨 Emergency Video Call
                        </button>
                      ) : (
                        <div className="flex-1 bg-gray-100 text-gray-500 px-4 py-2 rounded-lg text-center">
                          📝 Non-Emergency (Notes Only)
                        </div>
                      )}
                      <button
                        onClick={() => {
                          // Handle write note
                          console.log('Writing note for:', selectedNotificationAppointment.id);
                          setShowAppointmentDetailsModal(false);
                        }}
                        className="flex-1 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
                      >
                        📝 Write Note
                      </button>
                    </>
                  )}
                  <button
                    onClick={() => setShowAppointmentDetailsModal(false)}
                    className="px-6 py-2 bg-gray-300 text-gray-700 rounded-lg hover:bg-gray-400 focus:outline-none focus:ring-2 focus:ring-gray-500"
                  >
                    Close
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
      </div>
    </div>
  );
};

export default NotificationPanel;