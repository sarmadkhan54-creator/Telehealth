import React, { useState, useEffect, useRef } from 'react';
import { X, Bell, BellOff, Trash2, Check, Circle, Calendar, Video, FileText, UserPlus, AlertTriangle } from 'lucide-react';
import axios from 'axios';

const NotificationPanelNew = ({ user, isOpen, onClose, notifications, setNotifications, unreadCount, setUnreadCount }) => {
  const [activeTab, setActiveTab] = useState('all');
  const [selectedNotification, setSelectedNotification] = useState(null);
  const [showAppointmentModal, setShowAppointmentModal] = useState(false);
  const [swipedNotification, setSwipedNotification] = useState(null);
  const panelRef = useRef(null);

  import { BACKEND_URL, API_URL } from '../config';
  const API = API_URL;

  // Close panel when clicking outside
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (panelRef.current && !panelRef.current.contains(event.target) && isOpen) {
        onClose();
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [isOpen, onClose]);

  // Load notifications from localStorage on mount
  useEffect(() => {
    const savedNotifications = localStorage.getItem(`notifications_${user.id}`);
    if (savedNotifications) {
      try {
        const parsed = JSON.parse(savedNotifications);
        setNotifications(parsed);
        updateUnreadCount(parsed);
      } catch (error) {
        console.error('Error loading notifications:', error);
      }
    }
  }, [user.id]);

  // Save notifications to localStorage whenever they change
  useEffect(() => {
    if (notifications.length > 0) {
      localStorage.setItem(`notifications_${user.id}`, JSON.stringify(notifications));
    }
  }, [notifications, user.id]);

  const updateUnreadCount = (notificationsList) => {
    const unread = notificationsList.filter(n => !n.isRead).length;
    setUnreadCount(unread);
  };

  const markAsRead = async (notificationId) => {
    setNotifications(prev => {
      const updated = prev.map(n => 
        n.id === notificationId ? { ...n, isRead: true } : n
      );
      updateUnreadCount(updated);
      return updated;
    });
  };

  const markAllAsRead = () => {
    setNotifications(prev => {
      const updated = prev.map(n => ({ ...n, isRead: true }));
      updateUnreadCount(updated);
      return updated;
    });
  };

  const deleteNotification = (notificationId) => {
    setNotifications(prev => {
      const updated = prev.filter(n => n.id !== notificationId);
      updateUnreadCount(updated);
      return updated;
    });
  };

  const clearAllNotifications = () => {
    if (window.confirm('Delete all notifications?')) {
      setNotifications([]);
      setUnreadCount(0);
      localStorage.removeItem(`notifications_${user.id}`);
    }
  };

  const handleNotificationClick = async (notification) => {
    // Mark as read
    markAsRead(notification.id);

    // Close the notification panel
    onClose();

    // Handle different notification types
    if (notification.type === 'incoming_video_call' || notification.type === 'jitsi_call_invitation') {
      // Open video call
      if (notification.jitsi_url) {
        window.open(notification.jitsi_url, '_blank');
      }
    } else if (notification.appointment_id || notification.appointment?.id) {
      // Navigate to the appointment in the main dashboard
      const appointmentId = notification.appointment_id || notification.appointment?.id;
      
      // Scroll to the appointment in the list
      setTimeout(() => {
        const appointmentElement = document.querySelector(`[data-appointment-id="${appointmentId}"]`);
        if (appointmentElement) {
          appointmentElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
          
          // Highlight the appointment temporarily
          appointmentElement.classList.add('ring-4', 'ring-blue-500', 'ring-opacity-50');
          setTimeout(() => {
            appointmentElement.classList.remove('ring-4', 'ring-blue-500', 'ring-opacity-50');
          }, 3000);
        } else {
          // If appointment not found in current view, show details modal
          fetchAndShowAppointmentDetails(appointmentId);
        }
      }, 300);
    }
  };

  const fetchAndShowAppointmentDetails = async (appointmentId) => {
    try {
      const response = await axios.get(`${API}/appointments/${appointmentId}`);
      setSelectedNotification(response.data);
      setShowAppointmentModal(true);
    } catch (error) {
      console.error('Error fetching appointment:', error);
      alert('Could not load appointment details');
    }
  };

  const getNotificationIcon = (type) => {
    const iconMap = {
      'new_appointment_created': <Calendar className="w-5 h-5 text-blue-500" />,
      'emergency_appointment': <AlertTriangle className="w-5 h-5 text-red-500" />,
      'appointment_accepted': <Check className="w-5 h-5 text-green-500" />,
      'appointment_updated': <Calendar className="w-5 h-5 text-yellow-500" />,
      'incoming_video_call': <Video className="w-5 h-5 text-purple-500" />,
      'jitsi_call_invitation': <Video className="w-5 h-5 text-purple-500" />,
      'call_cancelled': <Video className="w-5 h-5 text-gray-500" />,
      'note_added': <FileText className="w-5 h-5 text-indigo-500" />,
      'user_created': <UserPlus className="w-5 h-5 text-green-500" />,
    };
    return iconMap[type] || <Bell className="w-5 h-5 text-gray-500" />;
  };

  const getTimeAgo = (timestamp) => {
    const now = new Date();
    const notificationTime = new Date(timestamp);
    const diffMs = now - notificationTime;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return notificationTime.toLocaleDateString();
  };

  const filteredNotifications = notifications.filter(n => {
    if (activeTab === 'unread') return !n.isRead;
    return true;
  }).sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));

  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div className="fixed inset-0 bg-black bg-opacity-50 z-[9998]" onClick={onClose}></div>

      {/* Notification Panel - Facebook/Instagram Style */}
      <div
        ref={panelRef}
        className="fixed top-0 right-0 h-full w-full sm:w-[420px] bg-white shadow-2xl z-[9999] transform transition-transform duration-300 ease-out"
        style={{ animation: 'slideIn 0.3s ease-out' }}
      >
        {/* Header */}
        <div className="sticky top-0 bg-white border-b border-gray-200 z-10">
          <div className="flex items-center justify-between p-4">
            <h2 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
              <Bell className="w-6 h-6 text-blue-500" />
              Notifications
            </h2>
            <button
              onClick={onClose}
              className="p-2 hover:bg-gray-100 rounded-full transition-colors"
              aria-label="Close"
            >
              <X className="w-5 h-5 text-gray-600" />
            </button>
          </div>

          {/* Tabs */}
          <div className="flex border-b border-gray-200">
            <button
              onClick={() => setActiveTab('all')}
              className={`flex-1 py-3 px-4 text-sm font-semibold transition-colors relative ${
                activeTab === 'all'
                  ? 'text-blue-600 border-b-2 border-blue-600'
                  : 'text-gray-600 hover:bg-gray-50'
              }`}
            >
              All
              {notifications.length > 0 && (
                <span className="ml-1 text-xs text-gray-500">({notifications.length})</span>
              )}
            </button>
            <button
              onClick={() => setActiveTab('unread')}
              className={`flex-1 py-3 px-4 text-sm font-semibold transition-colors relative ${
                activeTab === 'unread'
                  ? 'text-blue-600 border-b-2 border-blue-600'
                  : 'text-gray-600 hover:bg-gray-50'
              }`}
            >
              Unread
              {unreadCount > 0 && (
                <span className="ml-1 px-2 py-0.5 bg-red-500 text-white text-xs rounded-full">
                  {unreadCount}
                </span>
              )}
            </button>
          </div>

          {/* Actions Bar */}
          {notifications.length > 0 && (
            <div className="flex items-center justify-between p-3 bg-gray-50 border-b border-gray-200">
              <button
                onClick={markAllAsRead}
                className="text-sm text-blue-600 hover:text-blue-700 font-medium flex items-center gap-1"
              >
                <Check className="w-4 h-4" />
                Mark all read
              </button>
              <button
                onClick={clearAllNotifications}
                className="text-sm text-red-600 hover:text-red-700 font-medium flex items-center gap-1"
              >
                <Trash2 className="w-4 h-4" />
                Clear all
              </button>
            </div>
          )}
        </div>

        {/* Notifications List */}
        <div className="overflow-y-auto h-[calc(100%-180px)] bg-gray-50">
          {filteredNotifications.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-64 text-gray-400">
              <BellOff className="w-16 h-16 mb-4" />
              <p className="text-lg font-medium">No notifications</p>
              <p className="text-sm">You're all caught up!</p>
            </div>
          ) : (
            <div className="divide-y divide-gray-200">
              {filteredNotifications.map((notification) => (
                <NotificationItem
                  key={notification.id}
                  notification={notification}
                  onClick={() => handleNotificationClick(notification)}
                  onDelete={() => deleteNotification(notification.id)}
                  onMarkRead={() => markAsRead(notification.id)}
                  getIcon={getNotificationIcon}
                  getTimeAgo={getTimeAgo}
                  swipedId={swipedNotification}
                  setSwipedId={setSwipedNotification}
                />
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Appointment Details Modal */}
      {showAppointmentModal && selectedNotification && (
        <AppointmentDetailsModal
          appointment={selectedNotification}
          onClose={() => {
            setShowAppointmentModal(false);
            setSelectedNotification(null);
          }}
        />
      )}

      <style jsx>{`
        @keyframes slideIn {
          from {
            transform: translateX(100%);
          }
          to {
            transform: translateX(0);
          }
        }
      `}</style>
    </>
  );
};

// Individual Notification Item with Swipe Actions
const NotificationItem = ({ notification, onClick, onDelete, onMarkRead, getIcon, getTimeAgo, swipedId, setSwipedId }) => {
  const [touchStart, setTouchStart] = useState(null);
  const [touchEnd, setTouchEnd] = useState(null);
  const [swipeOffset, setSwipeOffset] = useState(0);

  const minSwipeDistance = 50;

  const onTouchStart = (e) => {
    setTouchEnd(null);
    setTouchStart(e.targetTouches[0].clientX);
  };

  const onTouchMove = (e) => {
    setTouchEnd(e.targetTouches[0].clientX);
    const distance = touchStart - e.targetTouches[0].clientX;
    if (distance > 0 && distance < 100) {
      setSwipeOffset(distance);
    }
  };

  const onTouchEnd = () => {
    if (!touchStart || !touchEnd) return;
    const distance = touchStart - touchEnd;
    const isLeftSwipe = distance > minSwipeDistance;
    
    if (isLeftSwipe) {
      setSwipedId(notification.id);
      setSwipeOffset(80);
    } else {
      setSwipeOffset(0);
      if (swipedId === notification.id) {
        setSwipedId(null);
      }
    }
  };

  return (
    <div className="relative overflow-hidden bg-white">
      {/* Swipe Actions Background */}
      <div className="absolute right-0 top-0 bottom-0 w-40 bg-gradient-to-l from-red-500 to-red-400 flex items-center justify-end pr-4 gap-2">
        <button
          onClick={(e) => {
            e.stopPropagation();
            onMarkRead();
            setSwipeOffset(0);
            setSwipedId(null);
          }}
          className="p-2 bg-white bg-opacity-20 rounded-full hover:bg-opacity-30"
        >
          <Check className="w-5 h-5 text-white" />
        </button>
        <button
          onClick={(e) => {
            e.stopPropagation();
            onDelete();
          }}
          className="p-2 bg-white bg-opacity-20 rounded-full hover:bg-opacity-30"
        >
          <Trash2 className="w-5 h-5 text-white" />
        </button>
      </div>

      {/* Notification Content */}
      <div
        className={`relative transition-transform duration-200 cursor-pointer ${
          !notification.isRead ? 'bg-blue-50' : 'bg-white'
        } hover:bg-gray-100`}
        style={{ transform: `translateX(-${swipeOffset}px)` }}
        onClick={onClick}
        onTouchStart={onTouchStart}
        onTouchMove={onTouchMove}
        onTouchEnd={onTouchEnd}
      >
        <div className="flex items-start gap-3 p-4">
          {/* Icon */}
          <div className={`flex-shrink-0 w-12 h-12 rounded-full flex items-center justify-center ${
            !notification.isRead ? 'bg-blue-100' : 'bg-gray-100'
          }`}>
            {getIcon(notification.type)}
          </div>

          {/* Content */}
          <div className="flex-1 min-w-0">
            <p className={`text-sm mb-1 ${!notification.isRead ? 'font-semibold text-gray-900' : 'text-gray-700'}`}>
              {notification.message || notification.title || 'New notification'}
            </p>
            <p className="text-xs text-gray-500 flex items-center gap-2">
              {getTimeAgo(notification.timestamp)}
              {!notification.isRead && (
                <Circle className="w-2 h-2 fill-blue-500 text-blue-500" />
              )}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

// Appointment Details Modal
const AppointmentDetailsModal = ({ appointment, onClose }) => {
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-[10000] p-4">
      <div className="bg-white rounded-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        <div className="sticky top-0 bg-white border-b border-gray-200 p-4 flex items-center justify-between">
          <h3 className="text-xl font-bold text-gray-900">Appointment Details</h3>
          <button
            onClick={onClose}
            className="p-2 hover:bg-gray-100 rounded-full transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6 space-y-4">
          {appointment.patient && (
            <div>
              <h4 className="font-semibold text-gray-700 mb-2">Patient Information</h4>
              <div className="bg-gray-50 p-4 rounded-lg space-y-2">
                <p><span className="font-medium">Name:</span> {appointment.patient.name}</p>
                <p><span className="font-medium">Age:</span> {appointment.patient.age}</p>
                <p><span className="font-medium">Gender:</span> {appointment.patient.gender}</p>
                {appointment.patient.history && (
                  <p><span className="font-medium">History:</span> {appointment.patient.history}</p>
                )}
                {appointment.patient.area_of_consultation && (
                  <p><span className="font-medium">Area:</span> {appointment.patient.area_of_consultation}</p>
                )}
              </div>
            </div>
          )}

          <div>
            <h4 className="font-semibold text-gray-700 mb-2">Appointment Status</h4>
            <p className="bg-gray-50 p-4 rounded-lg">
              <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                appointment.status === 'completed' ? 'bg-green-100 text-green-800' :
                appointment.status === 'pending' ? 'bg-yellow-100 text-yellow-800' :
                'bg-blue-100 text-blue-800'
              }`}>
                {appointment.status?.toUpperCase()}
              </span>
            </p>
          </div>
        </div>

        <div className="border-t border-gray-200 p-4 flex justify-end">
          <button
            onClick={onClose}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

export default NotificationPanelNew;
