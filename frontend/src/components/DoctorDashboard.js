import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { 
  Bell, 
  Phone, 
  User, 
  LogOut, 
  Calendar, 
  CheckCircle, 
  Clock, 
  AlertTriangle,
  MessageSquare,
  Video,
  Eye,
  Send,
  PhoneCall,
  X
} from 'lucide-react';
import NotificationPanel from './NotificationPanel';
import CallButton from './CallButton';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const DoctorDashboard = ({ user, onLogout }) => {
  const [appointments, setAppointments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [notifications, setNotifications] = useState([]);
  const [selectedAppointment, setSelectedAppointment] = useState(null);
  const [showAppointmentModal, setShowAppointmentModal] = useState(false);
  const [noteText, setNoteText] = useState('');
  const [appointmentNotes, setAppointmentNotes] = useState([]);
  const [showNotificationPanel, setShowNotificationPanel] = useState(false);
  const [unreadNotifications, setUnreadNotifications] = useState(0);

  // Helper function to show notifications (Service Worker compatible)
  const showNotification = async (title, options) => {
    if (!('Notification' in window) || Notification.permission !== 'granted') {
      return;
    }

    try {
      // Check if service worker is available
      if ('serviceWorker' in navigator && navigator.serviceWorker.controller) {
        const registration = await navigator.serviceWorker.ready;
        await registration.showNotification(title, options);
        console.log('✅ Service Worker notification shown:', title);
      } else {
        // Fallback: No service worker, use regular notification
        new Notification(title, options);
        console.log('✅ Regular notification shown:', title);
      }
    } catch (error) {
      console.log('Notification not supported or failed:', error.message);
    }
  };
  const navigate = useNavigate();

  const getNotificationTitle = (notification) => {
    switch (notification.type) {
      case 'emergency_appointment':
        return '🚨 Emergency Appointment';
      case 'new_appointment':
        return '📅 New Appointment';
      case 'appointment_accepted':
        return '✅ Appointment Accepted';
      case 'jitsi_call_invitation':
        return '📞 Incoming Video Call';
      default:
        return '📨 New Notification';
    }
  };

  const getNotificationMessage = (notification) => {
    switch (notification.type) {
      case 'emergency_appointment':
        return `Emergency consultation for ${notification.patient_name} from ${notification.provider_name}`;
      case 'new_appointment':
        return `New consultation for ${notification.patient_name} from ${notification.provider_name}`;
      case 'appointment_accepted':
        return `Dr. ${notification.doctor_name} accepted appointment for ${notification.patient_name}`;
      case 'jitsi_call_invitation':
        return `${notification.caller} is calling you for patient consultation`;
      default:
        return 'New notification received';
    }
  };

  useEffect(() => {
    fetchAppointments();
  }, []);

  useEffect(() => {
    // AGGRESSIVE Auto-refresh appointments every 2 seconds for GUARANTEED real-time sync
    console.log('🔄 Setting up ULTRA-AGGRESSIVE 2-second polling for Doctor Dashboard');
    const refreshInterval = setInterval(() => {
      console.log('⏰ Auto-refresh triggered (2s interval) - FORCING UPDATE');
      fetchAppointments();
    }, 2000); // Refresh every 2 seconds - GUARANTEED updates
    
    // Listen for appointment updates from notifications
    const handleAppointmentUpdate = () => {
      console.log('🔄 Appointment updated - refreshing dashboard');
      fetchAppointments();
    };

    window.addEventListener('appointmentUpdated', handleAppointmentUpdate);
    
    return () => {
      clearInterval(refreshInterval);
      window.removeEventListener('appointmentUpdated', handleAppointmentUpdate);
    };
  }, []);

  // Enhanced WebSocket setup with debounced refresh
  useEffect(() => {
    // CRITICAL: Only set up WebSocket if user is available
    if (!user || !user.id) {
      console.log('⚠️ Doctor WebSocket setup skipped - no user context available');
      return;
    }
    
    let refreshTimeout = null;
    
    // Debounced refresh function to prevent race conditions
    const debouncedRefresh = () => {
      if (refreshTimeout) {
        clearTimeout(refreshTimeout);
      }
      
      refreshTimeout = setTimeout(async () => {
        console.log('🔄 Debounced appointment refresh triggered');
        await fetchAppointments();
      }, 500); // Wait 500ms for multiple updates to settle
    };
    
    let reconnectAttempts = 0;
    const maxReconnectAttempts = 10;
    
    const connectWebSocket = () => {
      try {
        const wsUrl = `${BACKEND_URL.replace('https:', 'wss:').replace('http:', 'ws:')}/api/ws/${user.id}`;
        console.log(`🔌 Doctor WebSocket connecting (attempt ${reconnectAttempts + 1}):`, wsUrl);
        console.log(`   User ID: ${user.id}`);
        console.log(`   Backend URL: ${BACKEND_URL}`);
        const ws = new WebSocket(wsUrl);
        
        ws.onopen = () => {
          console.log('✅ Doctor WebSocket connected successfully - ALWAYS ONLINE MODE');
          reconnectAttempts = 0; // Reset on successful connection
          
          // Start heartbeat to keep connection alive
          const heartbeatInterval = setInterval(() => {
            if (ws && ws.readyState === WebSocket.OPEN) {
              console.log('💓 Doctor WebSocket heartbeat sent');
              ws.send(JSON.stringify({ type: 'heartbeat', timestamp: Date.now() }));
            }
          }, 30000); // Heartbeat every 30 seconds
          
          // Store interval ID for cleanup
          ws.heartbeatInterval = heartbeatInterval;
          
          // Send initial "online" status
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ 
              type: 'status_update', 
              status: 'online',
              role: 'doctor',
              user_id: user.id,
              timestamp: Date.now()
            }));
          }
        };
        
        ws.onmessage = (event) => {
          try {
            const notification = JSON.parse(event.data);
            console.log('📨 Doctor received WebSocket notification:', notification);
            
            // Handle heartbeat
            if (notification.type === 'heartbeat') {
              console.log('💓 Doctor WebSocket heartbeat received');
              return;
            }
            
            // Create comprehensive notification object
            const newNotification = {
              id: Date.now() + Math.random(),
              type: notification.type,
              title: getNotificationTitle(notification),
              message: getNotificationMessage(notification),
              timestamp: new Date(),
              data: notification,
              appointment_id: notification.appointment_id || notification.appointment?.id,  // CRITICAL: Add appointment_id
              appointment: notification.appointment,  // Include full appointment data if available
              isRead: false,
              priority: notification.type === 'emergency_appointment' ? 'high' : 'normal'
            };
            
            setNotifications(prev => [newNotification, ...prev.slice(0, 9)]);
            setUnreadNotifications(prev => prev + 1);
            
            // CRITICAL: Handle new appointment creation for DOCTOR INSTANT sync
            if (notification.type === 'new_appointment_created') {
              console.log('🚨 DOCTOR: NEW APPOINTMENT CREATED - FORCING IMMEDIATE SYNC:', notification);
              
              // Add appointment directly to doctor's state for INSTANT display
              if (notification.appointment) {
                setAppointments(prevAppointments => {
                  const newAppointment = notification.appointment;
                  // Check if appointment already exists to prevent duplicates
                  const exists = prevAppointments.some(apt => apt.id === newAppointment.id);
                  if (!exists) {
                    console.log('➕ DOCTOR: Adding new appointment to state immediately:', newAppointment.patient?.name);
                    return [...prevAppointments, newAppointment];
                  }
                  return prevAppointments;
                });
              }
              
              // Force immediate refresh
              fetchAppointments();
              
              // Show notification with full appointment details for doctors
              if (notification.show_in_notification) {
                const newNotification = {
                  id: Date.now() + Math.random(),
                  type: notification.type,
                  message: notification.message,
                  appointment: notification.appointment,
                  appointment_id: notification.appointment?.id || notification.appointment_id,  // CRITICAL: Add appointment_id
                  timestamp: new Date(notification.timestamp).toISOString(),
                  isRead: false
                };
                
                setNotifications(prev => [newNotification, ...prev]);
                setUnreadNotifications(prev => prev + 1);
              }
              
              // Visual toast notification for doctors
              const toast = document.createElement('div');
              toast.className = 'fixed top-4 right-4 bg-blue-500 text-white px-4 py-3 rounded-lg shadow-lg z-50 max-w-md';
              toast.innerHTML = `
                <div class="font-bold">🩺 New Patient Available!</div>
                <div class="text-sm">${notification.appointment?.patient?.name} - ${notification.appointment?.appointment_type?.toUpperCase()}</div>
                <div class="text-xs mt-1">From: ${notification.appointment?.provider_name}</div>
                <div class="text-xs">Area: ${notification.appointment?.patient?.area_of_consultation}</div>
              `;
              document.body.appendChild(toast);
              setTimeout(() => {
                if (document.body.contains(toast)) {
                  document.body.removeChild(toast);
                }
              }, 6000);
            }

            // ENHANCED: Real-time appointment sync for other doctor updates
            if (notification.type === 'emergency_appointment' || 
                notification.type === 'new_appointment' || 
                notification.type === 'appointment_accepted' || 
                notification.type === 'appointment_updated' ||
                notification.type === 'appointment_deleted' ||
                notification.type === 'appointment_cancelled' ||
                notification.type === 'appointment_created' ||
                notification.type === 'appointment_status_changed') {
              
              console.log('📅 REAL-TIME: Doctor appointment sync notification:', notification.type);
              
              // If appointment was deleted, remove it immediately from state
              if (notification.type === 'appointment_deleted' && notification.appointment_id) {
                console.log('🗑️ DOCTOR: Removing deleted appointment immediately:', notification.appointment_id);
                setAppointments(prevAppointments => 
                  prevAppointments.filter(apt => apt.id !== notification.appointment_id)
                );
              }
              
              // AGGRESSIVE REAL-TIME SYNC FOR DOCTORS
              console.log('🚨 DOCTOR: FORCING IMMEDIATE APPOINTMENT SYNC');
              
              // Immediate sync (0ms delay)
              fetchAppointments();
              
              // Force multiple UI refreshes
              setLoading(prev => !prev);
              setTimeout(() => setLoading(false), 10);
              
              // More aggressive sync attempts
              setTimeout(() => {
                console.log('🔄 DOCTOR AGGRESSIVE sync #1 after 100ms');
                fetchAppointments();
                setLoading(prev => !prev);
                setTimeout(() => setLoading(false), 10);
              }, 100);
              
              setTimeout(() => {
                console.log('🔄 DOCTOR AGGRESSIVE sync #2 after 500ms');
                fetchAppointments();
              }, 500);
              
              setTimeout(() => {
                console.log('🔄 DOCTOR AGGRESSIVE sync #3 after 1 second');
                fetchAppointments();
              }, 1000);
              
              setTimeout(() => {
                console.log('🔄 DOCTOR FINAL sync after 2 seconds');
                fetchAppointments();
              }, 2000);
              
              // Show visual feedback for new appointments
              if (notification.type === 'emergency_appointment' || notification.type === 'new_appointment') {
                const toast = document.createElement('div');
                toast.className = 'fixed top-4 right-4 bg-blue-500 text-white px-4 py-2 rounded-lg shadow-lg z-50';
                toast.textContent = `🚨 New ${notification.type === 'emergency_appointment' ? 'EMERGENCY' : ''} appointment available!`;
                document.body.appendChild(toast);
                setTimeout(() => document.body.removeChild(toast), 4000);
              }
            }
            
            // Show browser notifications for critical events
            if (notification.type === 'emergency_appointment') {
              if (Notification.permission === 'granted') {
                showNotification('🚨 Emergency Appointment', {
                  body: `${notification.patient_name || 'Patient'} needs immediate consultation`,
                  icon: '/favicon.ico',
                  requireInteraction: true
                });
              }
            } else if (notification.type === 'video_call_invitation') {
              if (Notification.permission === 'granted') {
                showNotification('📞 Video Call Invitation', {
                  body: `${notification.caller || 'Someone'} is inviting you to a video call`,
                  icon: '/favicon.ico',
                  requireInteraction: true
                });
              }
            }
          } catch (error) {
            console.error('Error processing doctor WebSocket notification:', error);
          }
        };

        ws.onerror = (error) => {
          console.error('❌ Doctor WebSocket error:', error);
        };

        ws.onclose = () => {
          console.log('🔌 Doctor WebSocket disconnected');
          
          // Clear refresh timeout on disconnect
          if (refreshTimeout) {
            clearTimeout(refreshTimeout);
          }
          
          // Implement exponential backoff reconnection
          if (reconnectAttempts < maxReconnectAttempts) {
            const delay = Math.min(1000 * Math.pow(2, reconnectAttempts), 30000); // Max 30 seconds
            console.log(`🔄 Doctor WebSocket reconnecting in ${delay}ms (attempt ${reconnectAttempts + 1}/${maxReconnectAttempts})`);
            
            setTimeout(() => {
              reconnectAttempts++;
              connectWebSocket();
            }, delay);
          } else {
            console.error('❌ Doctor WebSocket max reconnection attempts reached');
          }
        };

        // Request notification permission
        if (Notification.permission === 'default') {
          Notification.requestPermission();
        }

        return () => ws.close();
        
      } catch (error) {
        console.error('❌ Error creating doctor WebSocket:', error);
        
        // Retry after delay
        if (reconnectAttempts < maxReconnectAttempts) {
          setTimeout(() => {
            reconnectAttempts++;
            connectWebSocket();
          }, 1000 * Math.pow(2, reconnectAttempts));
        }
      }
    };

    connectWebSocket();
    
    // Cleanup on unmount
    return () => {
      if (refreshTimeout) {
        clearTimeout(refreshTimeout);
      }
    };
  }, [user.id, BACKEND_URL]);

  const fetchAppointments = async () => {
    try {
      console.log('Fetching appointments for doctor...');
      const response = await axios.get(`${API}/appointments`);
      console.log('Appointments fetched:', response.data.length, 'appointments');
      setAppointments(response.data);
    } catch (error) {
      console.error('Error fetching appointments:', error);
      if (error.response?.status === 401) {
        console.log('Authentication error - user might need to login again');
        // The axios interceptor will handle this
      } else {
        const errorMessage = error.response?.data?.detail || 'Error loading appointments. Please refresh the page.';
        console.error('Appointment fetch error:', errorMessage);
      }
    } finally {
      setLoading(false);
    }
  };

  // Removed accept functionality - doctors can now directly video call without accepting

  const handleVideoCall = async (appointment) => {
    console.log('🎥 Starting WhatsApp-like video call for appointment:', appointment.id);
    console.log('🎯 Appointment details:', {
      id: appointment.id,
      type: appointment.appointment_type,
      patient: appointment.patient?.name,
      provider_id: appointment.provider_id
    });
    
    // Check appointment type restrictions
    if (appointment.appointment_type === 'non_emergency') {
      alert('❌ Video calls are not allowed for non-emergency appointments. Please use notes instead.');
      return;
    }
    
    try {
      console.log('📡 Sending video call request to backend...');
      
      // Use the new WhatsApp-like video calling system
      const response = await axios.post(`${API}/video-call/start/${appointment.id}`);
      
      console.log('📞 Video call response:', response.data);
      
      if (response.data.success) {
        const { jitsi_url, call_attempt, message, provider_notified, call_id } = response.data;
        
        console.log(`✅ Emergency video call initiated (attempt ${call_attempt}):`);
        console.log(`   Jitsi URL: ${jitsi_url}`);
        console.log(`   Provider notified: ${provider_notified}`);
        console.log(`   Message: ${message}`);
        console.log(`   Call ID: ${call_id}`);
        
        // Enhanced Jitsi opening with moderator settings
        const enhancedJitsiUrl = `${jitsi_url}&userInfo.displayName=Dr.${user.full_name}&config.enableWelcomePage=false&config.prejoinPageEnabled=false&config.startWithVideoMuted=false&config.startWithAudioMuted=false`;
        
        // Open Jitsi video call in new window with enhanced settings
        const jitsiWindow = window.open(enhancedJitsiUrl, `jitsi_call_${appointment.id}`, 'width=1200,height=800,scrollbars=yes,resizable=yes,location=yes,menubar=no,toolbar=no');
        
        // CRITICAL: Monitor when doctor closes the Jitsi window
        if (jitsiWindow) {
          jitsiWindow.focus();
          console.log('✅ Jitsi window opened successfully');
          
          // Monitor window closure to cancel call for provider
          const windowCheckInterval = setInterval(async () => {
            if (jitsiWindow.closed) {
              console.log('🔴 Doctor closed Jitsi window - cancelling call for provider');
              clearInterval(windowCheckInterval);
              
              try {
                // Notify backend that doctor ended/cancelled the call
                await axios.post(`${API}/video-call/cancel/${appointment.id}`, {
                  call_id: call_id,
                  cancelled_by: 'doctor',
                  reason: 'Doctor closed call window'
                });
                console.log('✅ Call cancellation notification sent to provider');
              } catch (error) {
                console.error('❌ Error sending call cancellation:', error);
              }
            }
          }, 1000); // Check every second
          
          // Stop checking after 5 minutes (call probably ended normally)
          setTimeout(() => {
            clearInterval(windowCheckInterval);
            console.log('⏰ Stopped monitoring Jitsi window (5 minute timeout)');
          }, 300000);
          
        } else {
          console.error('❌ Failed to open Jitsi window - popup may be blocked');
          alert('⚠️ Popup blocked! Please allow popups for this site and try again.');
          
          // Cancel the call since window didn't open
          try {
            await axios.post(`${API}/video-call/cancel/${appointment.id}`, {
              call_id: call_id,
              cancelled_by: 'doctor',
              reason: 'Failed to open Jitsi window'
            });
          } catch (error) {
            console.error('❌ Error cancelling call:', error);
          }
        }
        
        // Force refresh appointments to update call history
        setTimeout(() => {
          console.log('🔄 Refreshing appointments after call initiation...');
          fetchAppointments();
        }, 1000);
      } else {
        console.error('❌ Video call failed:', response.data);
        alert('❌ Video call initiation failed. Please try again.');
      }
    } catch (error) {
      console.error('❌ Error starting video call:', error);
      console.error('   Status:', error.response?.status);
      console.error('   Response:', error.response?.data);
      
      const errorMessage = error.response?.data?.detail || 'Failed to start video call. Please try again.';
      alert(`❌ ${errorMessage}`);
    }
  };

  const handleWriteNote = (appointment) => {
    console.log('📝 Opening note composer for appointment:', appointment.id);
    setSelectedAppointment(appointment);
    setShowNoteModal(true);
    setNoteText('');
  };

  const [showNoteModal, setShowNoteModal] = useState(false);

  const handleSendNote = async () => {
    if (!noteText.trim()) {
      alert('Please enter a note before sending.');
      return;
    }

    if (!selectedAppointment) {
      alert('No appointment selected.');
      return;
    }

    try {
      console.log('📤 Sending note to provider for appointment:', selectedAppointment.id);
      console.log('📝 Note content:', noteText.trim());

      const response = await axios.post(`${API}/appointments/${selectedAppointment.id}/notes`, {
        note: noteText.trim(),
        note_type: selectedAppointment.appointment_type === 'emergency' ? 'emergency_note' : 'consultation_note',
        sender_role: 'doctor',
        timestamp: new Date().toISOString()
      });

      console.log('✅ Note sent successfully:', response.data);
      
      alert('✅ Note sent successfully to provider!');
      
      // FORCE FULL PAGE RELOAD to ensure fresh data
      window.location.reload();
      
    } catch (error) {
      console.error('❌ Error sending note:', error);
      console.error('❌ Error details:', error.response?.data);
      alert(`❌ Failed to send note: ${error.response?.data?.detail || error.message}`);
    }
  };

  const handleCompleteAppointment = async (appointmentId) => {
    try {
      console.log('Completing appointment:', appointmentId);
      
      const response = await axios.put(`${API}/appointments/${appointmentId}`, {
        status: 'completed'
      });
      
      console.log('Appointment completed successfully:', response.data);
      
      // Show success message
      alert('Appointment completed successfully!');
      
      // Force multiple refresh attempts to ensure UI updates
      setTimeout(async () => {
        console.log('First refresh after appointment completion...');
        await fetchAppointments();
      }, 100);
      
      setTimeout(async () => {
        console.log('Second refresh after appointment completion...');
        await fetchAppointments();
      }, 1000);
      
    } catch (error) {
      console.error('Error completing appointment:', error);
      const errorMessage = error.response?.data?.detail || 'Error completing appointment. Please try again.';
      alert(errorMessage);
      
      // Refresh appointments even on error to check current state
      await fetchAppointments();
    }
  };

  const startVideoCall = async (appointmentId) => {
    try {
      // Get Jitsi room for this appointment
      const response = await axios.get(`${API}/video-call/session/${appointmentId}`);
      
      // Extract room name and create a custom Jitsi URL with moderator disabled
      const { jitsi_url } = response.data;
      const roomName = jitsi_url.split('/').pop();
      
      // Create Jitsi URL with config to disable moderator requirement
      const configuredJitsiUrl = `https://meet.jit.si/${roomName}#config.startWithAudioMuted=false&config.startWithVideoMuted=false&config.requireDisplayName=false&config.enableWelcomePage=false&config.prejoinPageEnabled=false&config.enableModeratedDiscussion=false&config.disableModeratorIndicator=true&userInfo.displayName=${user.full_name}`;
      
      console.log(`Starting configured Jitsi meeting: ${configuredJitsiUrl}`);
      
      // Universal approach: Always open in new window/tab for better compatibility across all devices
      try {
        const newWindow = window.open(configuredJitsiUrl, '_blank', 'width=1200,height=800,scrollbars=yes,resizable=yes');
        if (newWindow) {
          newWindow.focus();
          console.log('✅ Video call opened in new window');
        } else {
          // Fallback for popup blockers
          console.log('⚠️ Popup blocked, using location.href fallback');
          window.location.href = configuredJitsiUrl;
        }
      } catch (error) {
        console.error('❌ Error opening video call, using fallback:', error);
        window.location.href = configuredJitsiUrl;
      }
      
    } catch (error) {
      console.error('Error starting video call:', error);
      alert('Error starting video call. Please try again.');
    }
  };

  const viewAppointmentDetails = async (appointment) => {
    try {
      const response = await axios.get(`${API}/appointments/${appointment.id}`);
      setSelectedAppointment(response.data);
      
      // Fetch appointment notes
      const notesResponse = await axios.get(`${API}/appointments/${appointment.id}/notes`);
      setAppointmentNotes(notesResponse.data);
      
      setShowAppointmentModal(true);
    } catch (error) {
      console.error('Error fetching appointment details:', error);
      alert('Error loading appointment details');
    }
  };

  // Note: sendNoteToProvider function removed - using handleSendNote instead

  const callProvider = (appointment) => {
    if (appointment.provider?.phone) {
      // In a real app, this would integrate with a calling system
      if (window.confirm(`Call ${appointment.provider.full_name} at ${appointment.provider.phone}?`)) {
        // Simulate call - in real app would use telephony integration
        alert(`Calling ${appointment.provider.phone}...\n\nIn a production app, this would initiate a real phone call.`);
      }
    } else {
      alert('Provider phone number not available');
    }
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleString();
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'pending': return 'status-pending';
      case 'accepted': return 'status-accepted';
      case 'completed': return 'status-completed';
      default: return 'status-pending';
    }
  };

  // All appointments: doctors can see ALL appointments (no accept required)
  const allAppointments = appointments.filter(apt => apt.status !== 'cancelled');
  
  // Active appointments: appointments currently being handled
  const activeAppointments = appointments.filter(apt => 
    apt.status === 'accepted' || apt.status === 'completed'
  );

  return (
    <div className="min-h-screen bg-gradient-to-br from-green-50 to-emerald-100">
      {/* Navigation Header */}
      <nav className="nav-header">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <img 
              src="https://customer-assets.emergentagent.com/job_medconnect-app/artifacts/syacsqjj_Greenstar-Logo.png" 
              alt="Greenstar Healthcare" 
              className="h-10 w-auto object-contain"
            />
            <div>
              <h1 className="nav-brand text-green-700">Greenstar Digital Health Solutions</h1>
              <p className="text-sm text-gray-600">Doctor Dashboard</p>
            </div>
          </div>
          
          <div className="flex items-center space-x-4">
            {/* Refresh button removed as requested */}
            
            {/* Notifications */}
            <button
              onClick={() => setShowNotificationPanel(true)}
              className="relative flex items-center space-x-2 px-3 py-2 text-green-600 hover:bg-green-50 rounded-lg transition-colors"
              title="Notifications"
            >
              <Bell className="w-6 h-6 text-gray-600" />
              {unreadNotifications > 0 && (
                <span className="absolute -top-1 -right-1 bg-red-500 text-white text-xs font-bold px-1 py-0.5 rounded-full min-w-[16px] h-4 flex items-center justify-center">
                  {unreadNotifications}
                </span>
              )}
              <span className="hidden sm:inline">Notifications</span>
            </button>
            
            <div className="text-right">
              <p className="font-semibold text-gray-900">Dr. {user.full_name}</p>
              <p className="text-sm text-gray-600">{user.specialty || 'General Medicine'}</p>
            </div>
            <button
              onClick={onLogout}
              className="flex items-center space-x-2 px-4 py-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
            >
              <LogOut className="w-4 h-4" />
              <span>Logout</span>
            </button>
          </div>
        </div>
      </nav>

      <div className="tablet-main">
        {/* Dashboard Stats */}
        <div className="dashboard-grid mb-8">
          <div className="glass-card">
            <h3 className="text-xl font-semibold text-gray-900 mb-4 flex items-center">
              <Bell className="w-6 h-6 mr-2 text-orange-600" />
              All Appointments
            </h3>
            <div className="text-center">
              <div className="text-3xl font-bold text-orange-600 mb-2">
                {allAppointments.length}
              </div>
              <p className="text-gray-600">Available for consultation</p>
            </div>
          </div>

          <div className="glass-card">
            <h3 className="text-xl font-semibold text-gray-900 mb-4 flex items-center">
              <CheckCircle className="w-6 h-6 mr-2 text-green-600" />
              Active Consultations
            </h3>
            <div className="text-center">
              <div className="text-3xl font-bold text-green-600 mb-2">
                {activeAppointments.length}
              </div>
              <p className="text-gray-600">In progress</p>
            </div>
          </div>

          <div className="glass-card">
            <h3 className="text-xl font-semibold text-gray-900 mb-4 flex items-center">
              <Calendar className="w-6 h-6 mr-2 text-green-600" />
              Today's Activity
            </h3>
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">Emergency:</span>
                <span className="font-semibold text-red-600">
                  {appointments.filter(apt => apt.appointment_type === 'emergency').length}
                </span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-gray-600">Completed:</span>
                <span className="font-semibold text-green-600">
                  {appointments.filter(apt => apt.status === 'completed').length}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Recent Notifications */}
        {notifications.length > 0 && (
          <div className="glass-card mb-8">
            <h2 className="text-xl font-bold text-gray-900 mb-4 flex items-center">
              <Bell className="w-6 h-6 mr-2 text-orange-600" />
              Recent Notifications
            </h2>
            <div className="space-y-3">
              {notifications.map((notification, index) => (
                <div key={index} className="bg-orange-50 border border-orange-200 rounded-lg p-3">
                  <div className="flex items-start space-x-3">
                    <AlertTriangle className="w-5 h-5 text-orange-600 mt-0.5" />
                    <div className="flex-1">
                      <p className="font-medium text-orange-900">
                        {notification.type === 'emergency_appointment' ? 'Emergency Appointment' : 'New Notification'}
                      </p>
                      <p className="text-sm text-orange-700">
                        {notification.patient_name && `Patient: ${notification.patient_name}`}
                        {notification.provider_name && ` | Provider: ${notification.provider_name}`}
                        {notification.provider_district && ` | District: ${notification.provider_district}`}
                      </p>
                      {notification.consultation_reason && (
                        <p className="text-sm text-orange-600 mt-1">
                          Reason: {notification.consultation_reason}
                        </p>
                      )}
                    </div>
                    <span className="text-xs text-orange-500">
                      {new Date(notification.timestamp).toLocaleTimeString()}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* All Appointments */}
        <div className="glass-card mb-8">
          <h2 className="text-2xl font-bold text-gray-900 mb-6 flex items-center">
            <Calendar className="w-7 h-7 mr-3 text-blue-600" />
            All Appointments
          </h2>

          {allAppointments.length === 0 ? (
            <div className="text-center py-8">
              <Calendar className="w-16 h-16 text-gray-300 mx-auto mb-4" />
              <p className="text-gray-500 text-lg">No appointments available</p>
            </div>
          ) : (
            <div className="space-y-4">
              {allAppointments.map((appointment) => (
                <div
                  key={appointment.id}
                  className={`appointment-card ${appointment.appointment_type === 'emergency' ? 'emergency' : 'non-emergency'}`}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center space-x-3 mb-2">
                        <h3 className="font-semibold text-lg text-gray-900">
                          {appointment.patient?.name}
                        </h3>
                        <span className={`px-3 py-1 rounded-full text-xs font-bold flex items-center space-x-1 ${
                          appointment.appointment_type === 'emergency' 
                            ? 'bg-red-100 text-red-800 border-2 border-red-300' 
                            : 'bg-blue-100 text-blue-800 border border-blue-300'
                        }`}>
                          {appointment.appointment_type === 'emergency' ? (
                            <>
                              <span>⚠️</span>
                              <span>EMERGENCY</span>
                            </>
                          ) : (
                            <>
                              <span>📅</span>
                              <span>NON-EMERGENCY</span>
                            </>
                          )}
                        </span>
                      </div>
                      
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm mb-4">
                        <div>
                          <p className="text-gray-600">Patient Info</p>
                          <p className="font-medium">
                            {appointment.patient?.age}y, {appointment.patient?.gender}
                          </p>
                        </div>
                        <div>
                          <p className="text-gray-600">Provider</p>
                          <p className="font-medium">
                            {appointment.provider?.full_name} ({appointment.provider?.district})
                          </p>
                        </div>
                        <div className="md:col-span-2">
                          <p className="text-gray-600">Patient History</p>
                          <p className="font-medium">
                            {appointment.patient?.history}
                          </p>
                        </div>
                        <div className="md:col-span-2">
                          <p className="text-gray-600">Area of Consultation</p>
                          <p className="font-medium">
                            {appointment.patient?.area_of_consultation}
                          </p>
                        </div>
                        
                        {/* Vitals */}
                        {appointment.patient?.vitals && Object.keys(appointment.patient.vitals).some(key => appointment.patient.vitals[key]) && (
                          <div className="md:col-span-2">
                            <p className="text-gray-600 mb-2">Patient Vitals</p>
                            <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs">
                              {appointment.patient.vitals.blood_pressure && (
                                <div className="bg-red-50 p-2 rounded">
                                  <p className="text-red-600">BP</p>
                                  <p className="font-medium">{appointment.patient.vitals.blood_pressure}</p>
                                </div>
                              )}
                              {appointment.patient.vitals.heart_rate && (
                                <div className="bg-pink-50 p-2 rounded">
                                  <p className="text-pink-600">HR</p>
                                  <p className="font-medium">{appointment.patient.vitals.heart_rate} bpm</p>
                                </div>
                              )}
                              {appointment.patient.vitals.temperature && (
                                <div className="bg-orange-50 p-2 rounded">
                                  <p className="text-orange-600">Temp</p>
                                  <p className="font-medium">{appointment.patient.vitals.temperature}°C</p>
                                </div>
                              )}
                              {appointment.patient.vitals.oxygen_saturation && (
                                <div className="bg-blue-50 p-2 rounded">
                                  <p className="text-blue-600">O2 Sat</p>
                                  <p className="font-medium">{appointment.patient.vitals.oxygen_saturation}%</p>
                                </div>
                              )}
                              {appointment.patient.vitals.hb && (
                                <div className={`p-2 rounded ${
                                  appointment.patient.vitals.hb >= 7 && appointment.patient.vitals.hb <= 18 
                                    ? 'bg-green-50' : 'bg-red-50'
                                }`}>
                                  <p className={`${
                                    appointment.patient.vitals.hb >= 7 && appointment.patient.vitals.hb <= 18 
                                      ? 'text-green-600' : 'text-red-600'
                                  }`}>💉 Hb</p>
                                  <p className="font-medium">{appointment.patient.vitals.hb} g/dL</p>
                                </div>
                              )}
                              {appointment.patient.vitals.sugar_level && (
                                <div className={`p-2 rounded ${
                                  appointment.patient.vitals.sugar_level >= 70 && appointment.patient.vitals.sugar_level <= 200 
                                    ? 'bg-green-50' : 'bg-red-50'
                                }`}>
                                  <p className={`${
                                    appointment.patient.vitals.sugar_level >= 70 && appointment.patient.vitals.sugar_level <= 200 
                                      ? 'text-green-600' : 'text-red-600'
                                  }`}>🍬 Sugar</p>
                                  <p className="font-medium">{appointment.patient.vitals.sugar_level} mg/dL</p>
                                </div>
                              )}
                            </div>
                          </div>
                        )}
                      </div>
                    </div>

                    <div className="ml-4 flex flex-col space-y-2">
                      {/* Video Call ONLY for Emergency appointments */}
                      {appointment.appointment_type === 'emergency' ? (
                        <button
                          onClick={() => handleVideoCall(appointment)}
                          className="btn-primary flex items-center space-x-2 bg-red-600 hover:bg-red-700"
                        >
                          <Video className="w-4 h-4" />
                          <span>Emergency Call</span>
                        </button>
                      ) : (
                        <div className="text-sm text-gray-500 italic">
                          📝 Non-Emergency: Notes Only
                        </div>
                      )}
                      
                      {/* Write Note available for ALL appointment types */}
                      <button
                        onClick={() => handleWriteNote(appointment)}
                        className={`flex items-center space-x-2 px-3 py-2 rounded ${
                          appointment.appointment_type === 'emergency' 
                            ? 'btn-secondary' 
                            : 'btn-primary bg-blue-600 hover:bg-blue-700 text-white'
                        }`}
                      >
                        <MessageSquare className="w-4 h-4" />
                        <span>Send Note to Provider</span>
                      </button>
                      
                      <button
                        onClick={() => viewAppointmentDetails(appointment)}
                        className="btn-tertiary flex items-center space-x-2"
                      >
                        <Eye className="w-4 h-4" />
                        <span>View Details</span>
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Active Consultations */}
        <div className="glass-card">
          <h2 className="text-2xl font-bold text-gray-900 mb-6 flex items-center">
            <Video className="w-7 h-7 mr-3 text-green-600" />
            Active Consultations
          </h2>

          {activeAppointments.length === 0 ? (
            <div className="text-center py-8">
              <Video className="w-16 h-16 text-gray-300 mx-auto mb-4" />
              <p className="text-gray-500 text-lg">No active consultations</p>
            </div>
          ) : (
            <div className="space-y-4">
              {activeAppointments.map((appointment) => (
                <div
                  key={appointment.id}
                  className={`appointment-card ${appointment.appointment_type === 'emergency' ? 'emergency' : 'non-emergency'}`}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center space-x-3 mb-2">
                        <h3 className="font-semibold text-lg text-gray-900">
                          {appointment.patient?.name}
                        </h3>
                        <span className={`status-badge ${getStatusColor(appointment.status)}`}>
                          {appointment.status}
                        </span>
                        <span className={`px-3 py-1 rounded-full text-xs font-bold flex items-center space-x-1 ${
                          appointment.appointment_type === 'emergency' 
                            ? 'bg-red-100 text-red-800 border-2 border-red-300' 
                            : 'bg-blue-100 text-blue-800 border border-blue-300'
                        }`}>
                          {appointment.appointment_type === 'emergency' ? (
                            <>
                              <span>⚠️</span>
                              <span>EMERGENCY</span>
                            </>
                          ) : (
                            <>
                              <span>📅</span>
                              <span>NON-EMERGENCY</span>
                            </>
                          )}
                        </span>
                      </div>
                      
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                        <div>
                          <p className="text-gray-600">Patient Info</p>
                          <p className="font-medium">
                            {appointment.patient?.age}y, {appointment.patient?.gender}
                          </p>
                        </div>
                        <div>
                          <p className="text-gray-600">Provider</p>
                          <p className="font-medium">
                            {appointment.provider?.full_name} ({appointment.provider?.district})
                          </p>
                        </div>
                        <div className="md:col-span-2">
                          <p className="text-gray-600">Patient History</p>
                          <p className="font-medium">
                            {appointment.patient?.history}
                          </p>
                        </div>
                        <div className="md:col-span-2">
                          <p className="text-gray-600">Area of Consultation</p>
                          <p className="font-medium">
                            {appointment.patient?.area_of_consultation}
                          </p>
                        </div>
                      </div>
                    </div>

                    <div className="ml-4 flex flex-col space-y-2">
                      {/* Emergency appointments: Show Video Call button */}
                      {appointment.appointment_type === 'emergency' && (
                        <button
                          onClick={() => handleVideoCall(appointment)}
                          className="bg-red-500 hover:bg-red-600 text-white px-4 py-2 rounded-lg flex items-center space-x-2 transition-colors"
                        >
                          <Video className="w-4 h-4" />
                          <span>Video Call</span>
                        </button>
                      )}
                      
                      {/* All appointments: Show Write Note button */}
                      <button
                        onClick={() => {
                          setSelectedAppointment(appointment);
                          setShowNoteModal(true);
                        }}
                        className="bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded-lg flex items-center space-x-2 transition-colors"
                      >
                        <MessageSquare className="w-4 h-4" />
                        <span>Write Note</span>
                      </button>
                      
                      {/* View Details button */}
                      <button
                        onClick={() => viewAppointmentDetails(appointment)}
                        className="bg-gray-500 hover:bg-gray-600 text-white px-4 py-2 rounded-lg flex items-center space-x-2 transition-colors"
                      >
                        <Eye className="w-4 h-4" />
                        <span>View Details</span>
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Note Compose Modal */}
      {showNoteModal && selectedAppointment && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg max-w-md w-full max-h-[80vh] overflow-y-auto">
            <div className="p-6">
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-xl font-bold text-gray-900">
                  📝 Send Note to Provider
                </h2>
                <button
                  onClick={() => setShowNoteModal(false)}
                  className="text-gray-400 hover:text-gray-600"
                >
                  <X className="w-6 h-6" />
                </button>
              </div>

              <div className="mb-4">
                <p className="text-sm text-gray-600">
                  <strong>Patient:</strong> {selectedAppointment.patient?.name}
                </p>
                <p className="text-sm text-gray-600">
                  <strong>Type:</strong> {selectedAppointment.appointment_type === 'emergency' ? '🚨 Emergency' : '📅 Non-Emergency'}
                </p>
                <p className="text-sm text-gray-600">
                  <strong>Provider:</strong> {selectedAppointment.provider_name || 'Unknown Provider'}
                </p>
              </div>

              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Your Note/Message to Provider:
                </label>
                <textarea
                  value={noteText}
                  onChange={(e) => setNoteText(e.target.value)}
                  rows={6}
                  className="w-full p-3 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Enter your consultation notes, recommendations, or questions for the provider..."
                  maxLength={1000}
                />
                <p className="text-xs text-gray-500 mt-1">
                  {noteText.length}/1000 characters
                </p>
              </div>

              <div className="flex space-x-3">
                <button
                  onClick={handleSendNote}
                  className="flex-1 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  📤 Send Note
                </button>
                <button
                  onClick={() => setShowNoteModal(false)}
                  className="flex-1 bg-gray-300 text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-400 focus:outline-none focus:ring-2 focus:ring-gray-500"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Appointment Details Modal */}
      {showAppointmentModal && selectedAppointment && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="glass-card max-w-4xl w-full max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-2xl font-bold text-gray-900">Appointment Details</h3>
              <button
                onClick={() => setShowAppointmentModal(false)}
                className="text-gray-500 hover:text-gray-700 text-xl"
              >
                ×
              </button>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Patient Information */}
              <div className="glass-card">
                <h4 className="text-lg font-semibold text-gray-900 mb-4">Patient Information</h4>
                <div className="space-y-3">
                  <div>
                    <p className="text-sm text-gray-600">Name</p>
                    <p className="font-medium">{selectedAppointment.patient?.name}</p>
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <p className="text-sm text-gray-600">Age</p>
                      <p className="font-medium">{selectedAppointment.patient?.age} years</p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-600">Gender</p>
                      <p className="font-medium">{selectedAppointment.patient?.gender}</p>
                    </div>
                  </div>
                  <div>
                    <p className="text-sm text-gray-600">Patient History</p>
                    <p className="font-medium">{selectedAppointment.patient?.history}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-600">Area of Consultation</p>
                    <p className="font-medium">{selectedAppointment.patient?.area_of_consultation}</p>
                  </div>
                </div>

                {/* Patient Vitals */}
                {selectedAppointment.patient?.vitals && Object.keys(selectedAppointment.patient.vitals).some(key => selectedAppointment.patient.vitals[key]) && (
                  <div className="mt-6">
                    <h5 className="text-md font-semibold text-gray-900 mb-3">Vitals</h5>
                    <div className="grid grid-cols-2 gap-3">
                      {selectedAppointment.patient.vitals.blood_pressure && (
                        <div className="bg-red-50 p-3 rounded-lg">
                          <p className="text-sm text-red-600">Blood Pressure</p>
                          <p className="font-medium">{selectedAppointment.patient.vitals.blood_pressure}</p>
                        </div>
                      )}
                      {selectedAppointment.patient.vitals.heart_rate && (
                        <div className="bg-pink-50 p-3 rounded-lg">
                          <p className="text-sm text-pink-600">Heart Rate</p>
                          <p className="font-medium">{selectedAppointment.patient.vitals.heart_rate} bpm</p>
                        </div>
                      )}
                      {selectedAppointment.patient.vitals.temperature && (
                        <div className="bg-orange-50 p-3 rounded-lg">
                          <p className="text-sm text-orange-600">Temperature</p>
                          <p className="font-medium">{selectedAppointment.patient.vitals.temperature}°C</p>
                        </div>
                      )}
                      {selectedAppointment.patient.vitals.oxygen_saturation && (
                        <div className="bg-blue-50 p-3 rounded-lg">
                          <p className="text-sm text-blue-600">O2 Saturation</p>
                          <p className="font-medium">{selectedAppointment.patient.vitals.oxygen_saturation}%</p>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>

              {/* Provider & Appointment Info */}
              <div className="space-y-4">
                <div className="glass-card">
                  <h4 className="text-lg font-semibold text-gray-900 mb-4">Provider Information</h4>
                  <div className="space-y-3">
                    <div>
                      <p className="text-sm text-gray-600">Name</p>
                      <p className="font-medium">{selectedAppointment.provider?.full_name}</p>
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <p className="text-sm text-gray-600">District</p>
                        <p className="font-medium">{selectedAppointment.provider?.district}</p>
                      </div>
                      <div>
                        <p className="text-sm text-gray-600">Phone</p>
                        <p className="font-medium">{selectedAppointment.provider?.phone}</p>
                      </div>
                    </div>
                  </div>
                </div>

                <div className="glass-card">
                  <h4 className="text-lg font-semibold text-gray-900 mb-4">Appointment Status</h4>
                  <div className="space-y-3">
                    <div className="flex items-center space-x-3">
                      <span className={`px-3 py-1 rounded-full text-sm font-bold flex items-center space-x-1 ${
                        selectedAppointment.appointment_type === 'emergency' 
                          ? 'bg-red-100 text-red-800 border-2 border-red-300' 
                          : 'bg-blue-100 text-blue-800 border border-blue-300'
                      }`}>
                        {selectedAppointment.appointment_type === 'emergency' ? (
                          <>
                            <span>⚠️</span>
                            <span>EMERGENCY</span>
                          </>
                        ) : (
                          <>
                            <span>📅</span>
                            <span>NON-EMERGENCY</span>
                          </>
                        )}
                      </span>
                      <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                        selectedAppointment.status === 'pending' ? 'bg-yellow-100 text-yellow-800' :
                        selectedAppointment.status === 'accepted' ? 'bg-green-100 text-green-800' :
                        'bg-blue-100 text-blue-800'
                      }`}>
                        {selectedAppointment.status.toUpperCase()}
                      </span>
                    </div>
                    <div>
                      <p className="text-sm text-gray-600">Created</p>
                      <p className="font-medium">{formatDate(selectedAppointment.created_at)}</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Notes Section */}
            <div className="mt-6">
              <h4 className="text-lg font-semibold text-gray-900 mb-4">Communication Notes</h4>
              
              {/* Existing Notes */}
              <div className="space-y-3 mb-4 max-h-40 overflow-y-auto">
                {appointmentNotes.length > 0 ? (
                  appointmentNotes.map((note, index) => (
                    <div key={index} className={`p-3 rounded-lg ${
                      note.sender_role === 'doctor' ? 'bg-blue-50 ml-8' : 'bg-green-50 mr-8'
                    }`}>
                      <div className="flex justify-between items-start mb-1">
                        <span className="font-medium text-sm">
                          {note.sender_role === 'doctor' ? 'Dr.' : ''} {note.sender_name}
                        </span>
                        <span className="text-xs text-gray-500">
                          {new Date(note.timestamp).toLocaleString()}
                        </span>
                      </div>
                      <p className="text-sm">{note.note}</p>
                    </div>
                  ))
                ) : (
                  <p className="text-gray-500 text-center py-4">No notes yet</p>
                )}
              </div>

              {/* Add New Note (for ALL appointments) */}
              <div className="bg-blue-50 p-4 rounded-lg">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Send Note to Provider
                </label>
                <div className="flex space-x-3">
                  <textarea
                    value={noteText}
                    onChange={(e) => setNoteText(e.target.value)}
                    className="flex-1 form-input"
                    rows={3}
                    placeholder="Type your note to the provider..."
                  />
                  <button
                    onClick={handleSendNote}
                    disabled={!noteText.trim()}
                    className="btn-primary flex items-center space-x-2 self-start disabled:opacity-50"
                  >
                    <Send className="w-4 h-4" />
                    <span>Send</span>
                  </button>
                </div>
              </div>
            </div>

            {/* Action Buttons */}
            <div className="flex justify-end space-x-4 mt-6 pt-6 border-t">
              {/* Emergency appointments: Show Video Call button */}
              {selectedAppointment.appointment_type === 'emergency' && (
                <button
                  onClick={() => handleVideoCall(selectedAppointment)}
                  className="bg-red-500 hover:bg-red-600 text-white px-4 py-2 rounded-lg flex items-center space-x-2 transition-colors"
                >
                  <Video className="w-4 h-4" />
                  <span>Video Call</span>
                </button>
              )}
              
              {/* All appointments: Show Write Note button */}
              <button
                onClick={() => {
                  setShowAppointmentModal(false);
                  setShowNoteModal(true);
                }}
                className="bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded-lg flex items-center space-x-2 transition-colors"
              >
                <MessageSquare className="w-4 h-4" />
                <span>Write Note</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Notification Panel */}
      <NotificationPanel
        user={user}
        isOpen={showNotificationPanel}
        onClose={() => setShowNotificationPanel(false)}
      />
    </div>
  );
};

export default DoctorDashboard;