import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Plus, Clock, AlertTriangle, User, LogOut, Calendar, Phone, PhoneOff, X, Eye, Send, Bell, MessageSquare } from 'lucide-react';
import NotificationSettings from './NotificationSettings';
import NotificationPanel from './NotificationPanel';
import CallButton from './CallButton';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const Dashboard = ({ user, onLogout }) => {
  const [appointments, setAppointments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedAppointment, setSelectedAppointment] = useState(null);
  const [showAppointmentModal, setShowAppointmentModal] = useState(false);
  const [showProviderNoteModal, setShowProviderNoteModal] = useState(false);
  const [providerNoteText, setProviderNoteText] = useState('');
  const [noteText, setNoteText] = useState('');
  const [appointmentNotes, setAppointmentNotes] = useState([]);
  const [notifications, setNotifications] = useState([]);
  const [unreadNotifications, setUnreadNotifications] = useState(0);
  const [showVideoCallInvitation, setShowVideoCallInvitation] = useState(false);
  const [videoCallInvitation, setVideoCallInvitation] = useState(null);
  const [isRinging, setIsRinging] = useState(false);
  const [ringingAudio, setRingingAudio] = useState(null);
  const [showNotificationSettings, setShowNotificationSettings] = useState(false);
  const [showNotificationPanel, setShowNotificationPanel] = useState(false);
  const [reconnectTimeout, setReconnectTimeout] = useState(null);
  const navigate = useNavigate();

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

  useEffect(() => {
    fetchAppointments();
    setupWebSocket();
    
    // Request notification permissions immediately (simpler approach)
    const requestNotificationPermission = async () => {
      try {
        if ('Notification' in window && Notification.permission === 'default') {
          const permission = await Notification.requestPermission();
          console.log('📱 Notification permission:', permission);
          
          if (permission === 'granted') {
            console.log('✅ Notifications enabled successfully');
            
            // Test notification
            showNotification('✅ Notifications Enabled', {
              body: 'You will now receive video call and appointment notifications',
              icon: '/favicon.ico'
            });
          }
        }
      } catch (error) {
        console.error('Error requesting notification permission:', error);
      }
    };
    
    // Auto-request notification permission after component mounts
    setTimeout(requestNotificationPermission, 2000);
    
    // Keep service alive - prevent Android Doze mode and background throttling
    const keepAlive = () => {
      // Send periodic keepalive signals
      const keepAliveInterval = setInterval(() => {
        // Wake lock API for preventing sleep (if supported)
        if ('wakeLock' in navigator) {
          navigator.wakeLock.request('screen').catch(err => {
            console.log('Wake Lock request failed:', err);
          });
        }
        
        // Page visibility API to detect background/foreground
        if (document.visibilityState === 'visible') {
          console.log('📱 Provider service ACTIVE - keeping online');
        }
        
        // Service worker keepalive
        if ('serviceWorker' in navigator) {
          navigator.serviceWorker.ready.then(() => {
            console.log('🔄 Service Worker keepalive signal');
          });
        }
        
      }, 60000); // Every minute
      
      return keepAliveInterval;
    };
    
    const keepAliveInterval = keepAlive();
    
    return () => {
      clearInterval(keepAliveInterval);
    };
  }, []);

  useEffect(() => {
    // AGGRESSIVE Auto-refresh appointments every 5 seconds for real-time sync
    console.log('🔄 Setting up aggressive 5-second polling for Provider Dashboard');
    const refreshInterval = setInterval(() => {
      console.log('⏰ Provider auto-refresh triggered (5s interval)');
      fetchAppointments();
    }, 5000); // Refresh every 5 seconds for real-time feel
    return () => clearInterval(refreshInterval);
  }, []);

  const setupWebSocket = () => {
    let reconnectAttempts = 0;
    const maxReconnectAttempts = 50; // Increased for persistence
    let heartbeatInterval = null;
    let ws = null;
    
    const connectWebSocket = () => {
      try {
        // Construct WebSocket URL properly for mobile and desktop
        let wsUrl;
        if (BACKEND_URL.startsWith('https://')) {
          wsUrl = BACKEND_URL.replace('https://', 'wss://') + `/api/ws/${user.id}`;
        } else if (BACKEND_URL.startsWith('http://')) {
          wsUrl = BACKEND_URL.replace('http://', 'ws://') + `/api/ws/${user.id}`;
        } else {
          // Fallback for relative URLs
          const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
          wsUrl = `${protocol}//${window.location.host}/api/ws/${user.id}`;
        }
        
        console.log(`🔌 Provider WebSocket connecting (attempt ${reconnectAttempts + 1}):`, wsUrl);
        
        ws = new WebSocket(wsUrl);
        
        ws.onopen = () => {
          console.log('✅ Provider WebSocket connected successfully - ALWAYS ONLINE MODE');
          reconnectAttempts = 0; // Reset on successful connection
          
          // Start heartbeat to keep connection alive
          heartbeatInterval = setInterval(() => {
            if (ws && ws.readyState === WebSocket.OPEN) {
              console.log('💓 Provider WebSocket heartbeat sent');
              ws.send(JSON.stringify({ type: 'heartbeat', timestamp: Date.now() }));
            }
          }, 30000); // Heartbeat every 30 seconds
          
          // Send initial "online" status
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ 
              type: 'status_update', 
              status: 'online',
              role: 'provider',
              user_id: user.id,
              timestamp: Date.now()
            }));
          }
        };
      
        ws.onmessage = (event) => {
          try {
            const notification = JSON.parse(event.data);
            console.log('📨 Provider received WebSocket notification:', notification);
            
            // CRITICAL: Handle new appointment creation for INSTANT sync
            if (notification.type === 'new_appointment_created') {
              console.log('🚨 NEW APPOINTMENT CREATED - FORCING IMMEDIATE SYNC:', notification);
              
              // Add appointment directly to state for INSTANT display
              if (notification.appointment) {
                setAppointments(prevAppointments => {
                  const newAppointment = notification.appointment;
                  // Check if appointment already exists to prevent duplicates
                  const exists = prevAppointments.some(apt => apt.id === newAppointment.id);
                  if (!exists) {
                    console.log('➕ Adding new appointment to state immediately:', newAppointment.patient?.name);
                    return [...prevAppointments, newAppointment];
                  }
                  return prevAppointments;
                });
              }
              
              // Force immediate refresh
              fetchAppointments();
              
              // Show notification with full appointment details
              if (notification.show_in_notification) {
                setNotifications(prev => [{
                  id: Date.now(),
                  type: notification.type,
                  message: notification.message,
                  appointment: notification.appointment,
                  timestamp: notification.timestamp,
                  read: false
                }, ...prev]);
                
                setUnreadNotifications(prev => prev + 1);
              }
              
              // Visual toast notification
              const toast = document.createElement('div');
              toast.className = 'fixed top-4 right-4 bg-green-500 text-white px-4 py-3 rounded-lg shadow-lg z-50 max-w-md';
              toast.innerHTML = `
                <div class="font-bold">✅ New Appointment Added!</div>
                <div class="text-sm">${notification.appointment?.patient?.name} - ${notification.appointment?.appointment_type}</div>
                <div class="text-xs mt-1">Provider: ${notification.appointment?.provider_name}</div>
              `;
              document.body.appendChild(toast);
              setTimeout(() => {
                if (document.body.contains(toast)) {
                  document.body.removeChild(toast);
                }
              }, 5000);
            }

            // ENHANCED: Real-time appointment sync for other updates
            if (notification.type === 'emergency_appointment' || 
                notification.type === 'new_appointment' || 
                notification.type === 'appointment_accepted' || 
                notification.type === 'appointment_updated' ||
                notification.type === 'appointment_deleted' ||
                notification.type === 'appointment_cancelled' ||
                notification.type === 'video_call_invitation' ||
                notification.type === 'appointment_created' ||
                notification.type === 'appointment_status_changed') {
              
              console.log('📅 REAL-TIME: Appointment sync notification received:', notification.type);
              
              // If appointment was deleted, remove it immediately from state
              if (notification.type === 'appointment_deleted' && notification.appointment_id) {
                console.log('🗑️ PROVIDER: Removing deleted appointment immediately:', notification.appointment_id);
                setAppointments(prevAppointments => 
                  prevAppointments.filter(apt => apt.id !== notification.appointment_id)
                );
              }
              
              // AGGRESSIVE REAL-TIME SYNC - NO MORE LOGOUT/LOGIN REQUIRED
              console.log('🚨 FORCING IMMEDIATE APPOINTMENT SYNC');
              
              // Immediate sync (0ms delay)
              fetchAppointments();
              
              // Force multiple UI refreshes
              setLoading(prev => !prev);
              setTimeout(() => setLoading(false), 10);
              
              // More aggressive sync attempts
              setTimeout(() => {
                console.log('🔄 AGGRESSIVE sync #1 after 100ms');
                fetchAppointments();
                setLoading(prev => !prev);
                setTimeout(() => setLoading(false), 10);
              }, 100);
              
              setTimeout(() => {
                console.log('🔄 AGGRESSIVE sync #2 after 500ms');
                fetchAppointments();
              }, 500);
              
              setTimeout(() => {
                console.log('🔄 AGGRESSIVE sync #3 after 1 second');
                fetchAppointments();
              }, 1000);
              
              setTimeout(() => {
                console.log('🔄 FINAL sync after 2 seconds');
                fetchAppointments();
              }, 2000);
              
              // Force page refresh if still not working after 5 seconds
              setTimeout(() => {
                console.log('🔄 EMERGENCY refresh check after 5 seconds');
                window.dispatchEvent(new Event('focus'));
              }, 5000);
              
              // Show visual notification to user
              if (notification.type === 'new_appointment' || notification.type === 'emergency_appointment') {
                // Create instant visual feedback
                const toast = document.createElement('div');
                toast.className = 'fixed top-4 right-4 bg-green-500 text-white px-4 py-2 rounded-lg shadow-lg z-50';
                toast.textContent = '✅ New appointment received - Dashboard updated!';
                document.body.appendChild(toast);
                setTimeout(() => document.body.removeChild(toast), 3000);
              }
            }
            
            // Handle REAL-TIME DOCTOR NOTES - ENHANCED NOTIFICATIONS
            if (notification.type === 'new_note' || notification.type === 'doctor_note' || notification.type === 'provider_note' || notification.type === 'emergency_provider_note') {
              console.log('📝 REAL-TIME: Enhanced note notification received:', notification);
              
              // Add enhanced note to notifications list
              setNotifications(prev => [{
                id: notification.note_id || Date.now(),
                type: notification.type,
                title: `📝 New Note from ${notification.sender_role === 'doctor' ? 'Dr.' : ''} ${notification.sender_name}`,
                message: notification.message,
                fullDetails: {
                  note: notification.note,
                  sender_name: notification.sender_name,
                  sender_role: notification.sender_role,
                  patient_name: notification.patient_name,
                  appointment_id: notification.appointment_id,
                  appointment_type: notification.appointment_type
                },
                timestamp: notification.timestamp,
                read: false,
                clickable: true,
                actionable: true
              }, ...prev]);
              
              setUnreadNotifications(prev => prev + 1);
              
              // Show immediate visual notification
              const noteToast = document.createElement('div');
              noteToast.className = 'fixed top-4 right-4 bg-blue-500 text-white px-4 py-3 rounded-lg shadow-lg z-50 max-w-md cursor-pointer';
              noteToast.innerHTML = `
                <div class="font-bold">📝 ${notification.message}</div>
                <div class="text-sm mt-1">${notification.note.substring(0, 100)}${notification.note.length > 100 ? '...' : ''}</div>
                <div class="text-xs mt-1 opacity-75">Patient: ${notification.patient_name}</div>
                <div class="text-xs mt-1 opacity-75">Click to view in notifications</div>
              `;
              
              // Make toast clickable to open notifications
              noteToast.onclick = () => {
                setShowNotificationPanel(true);
                document.body.removeChild(noteToast);
              };
              
              document.body.appendChild(noteToast);
              
              // Play notification sound
              playNotificationSound();
              
              // Auto-remove after 7 seconds
              setTimeout(() => {
                if (document.body.contains(noteToast)) {
                  document.body.removeChild(noteToast);
                }
              }, 7000);
              
              // Force refresh appointments to show new note
              fetchAppointments();
              
              console.log('✅ Note notification processed and added to notifications panel');
            }

            // Handle WhatsApp-like video call notifications (updated notification type)
            if (notification.type === 'incoming_video_call' || notification.type === 'jitsi_call_invitation') {
              console.log('📞 Received WhatsApp-like video call invitation:', notification);
              
              // Play ringing sound immediately
              playRingingSound();
              
              // Show video call invitation popup with Jitsi URL
              setVideoCallInvitation({
                jitsiUrl: notification.jitsi_url,
                roomName: notification.room_name,
                callerName: notification.doctor_name || notification.caller,
                callerRole: 'doctor',
                appointmentId: notification.appointment_id,
                appointmentType: 'emergency',  // WhatsApp-like calls are emergency only
                callAttempt: notification.call_attempt || 1,
                patient: notification.patient || {
                  name: "Unknown Patient",
                  age: "Unknown",
                  gender: "Unknown", 
                  history: "General consultation",
                  area_of_consultation: "General Medicine",
                  vitals: {}
                }
              });
              setShowVideoCallInvitation(true);
              
              // Auto-hide popup after 30 seconds
              setTimeout(() => {
                stopRingingSound();
                setShowVideoCallInvitation(false);
                setVideoCallInvitation(null);
              }, 30000);
              
              // Add notification to local state
              const newNotification = {
                id: Date.now() + Math.random(),
                type: notification.type,
                title: 'Incoming Video Call',
                message: `${notification.caller} is inviting you to a video consultation`,
                timestamp: new Date().toISOString(),
                isRead: false
              };
              setNotifications(prev => [newNotification, ...prev]);
              setUnreadNotifications(prev => prev + 1);

              // Send browser notification if permission granted
              if (Notification.permission === 'granted') {
                showNotification('📞 Incoming Video Call', {
                  body: `${notification.caller} is inviting you to a video consultation`,
                  icon: '/favicon.ico',
                  tag: 'video-call-invitation',
                  requireInteraction: true
                });
              }
            }
            
            // Handle other notification types with browser notifications
            if (Notification.permission === 'granted') {
              if (notification.type === 'appointment_accepted') {
                showNotification('✅ Appointment Accepted', {
                  body: `Doctor accepted your appointment for ${notification.patient_name}`,
                  icon: '/favicon.ico'
                });
              } else if (notification.type === 'emergency_appointment') {
                showNotification('🚨 Emergency Appointment', {
                  body: `New emergency appointment: ${notification.patient_name}`,
                  icon: '/favicon.ico',
                  requireInteraction: true
                });
              }
            }
          } catch (error) {
            console.error('Error parsing Provider WebSocket message:', error);
          }
        };

        ws.onerror = (error) => {
          console.error('❌ Provider WebSocket error:', error);
        };

        ws.onclose = (event) => {
          console.log('🔌 Provider WebSocket closed - RECONNECTING FOR ALWAYS ONLINE:', event.code, event.reason);
          
          // Clear heartbeat
          if (heartbeatInterval) {
            clearInterval(heartbeatInterval);
            heartbeatInterval = null;
          }
          
          // Clear any existing timeout
          if (reconnectTimeout) {
            clearTimeout(reconnectTimeout);
          }
          
          // Persistent reconnection for "Always Online" mode
          if (reconnectAttempts < maxReconnectAttempts) {
            const delay = Math.min(2000 + (reconnectAttempts * 1000), 10000); // Progressive delay, max 10s
            console.log(`🔄 Provider WebSocket PERSISTENT reconnect in ${delay}ms (attempt ${reconnectAttempts + 1}/${maxReconnectAttempts})`);
            
            const timeoutId = setTimeout(() => {
              reconnectAttempts++;
              connectWebSocket();
            }, delay);
            
            setReconnectTimeout(timeoutId);
          } else {
            console.error('❌ Provider WebSocket maximum reconnection attempts reached - resetting counter');
            // Reset and continue trying (Always Online mode)
            reconnectAttempts = 0;
            setTimeout(() => {
              console.log('🔄 Provider WebSocket restarting reconnection cycle');
              connectWebSocket();
            }, 5000);
          }
        };

      } catch (error) {
        console.error('❌ Error creating Provider WebSocket:', error);
        
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
  };

  const playRingingSound = () => {
    try {
      console.log('🔊 STARTING CALL RINGTONE - LOUD AND PERSISTENT');
      
      // Stop any existing ringing
      stopRingingSound();
      
      const context = new (window.AudioContext || window.webkitAudioContext)();
      
      const createRingTone = () => {
        const oscillator = context.createOscillator();
        const gainNode = context.createGain();
        
        oscillator.connect(gainNode);
        gainNode.connect(context.destination);
        
        // LOUD ringing frequency (classic phone ring at 800Hz)
        oscillator.frequency.setValueAtTime(800, context.currentTime);
        oscillator.type = 'sine';
        
        // HIGH VOLUME for incoming call
        gainNode.gain.setValueAtTime(0.7, context.currentTime); // Increased volume
        
        oscillator.start(context.currentTime);
        
        // Ring pattern: 1 second ring, 0.5 second pause
        setTimeout(() => {
          try {
            oscillator.stop();
          } catch (e) {
            console.log('Oscillator already stopped');
          }
        }, 1000);
        
        return oscillator;
      };
      
      // Start ringing immediately
      createRingTone();
      
      // Continue ringing every 1.5 seconds until stopped
      window.currentRingingInterval = setInterval(() => {
        console.log('🔊 RINGTONE CONTINUES - INCOMING CALL');
        createRingTone();
        
        // Also show browser notification
        if ('Notification' in window && Notification.permission === 'granted') {
          showNotification('📞 Incoming Video Call', {
            body: 'A doctor is calling you for consultation',
            icon: '/favicon.ico',
            requireInteraction: true
          });
        }
        
      }, 1500); // Ring every 1.5 seconds
      
      // Vibrate if supported (mobile devices)
      if (navigator.vibrate) {
        // Vibration pattern: vibrate 500ms, pause 500ms, repeat
        const vibratePattern = [500, 500];
        window.currentVibration = setInterval(() => {
          navigator.vibrate(vibratePattern);
        }, 1000);
      }
      
      console.log('🔊 RINGTONE STARTED - Will continue until call is answered or cancelled');
      
    } catch (error) {
      console.error('❌ Error starting ringtone:', error);
      // Fallback to system notification
      playNotificationSound();
      
      // Browser notification as backup
      if ('Notification' in window && Notification.permission === 'granted') {
        try {
          new Notification('📞 Incoming Call', {
            body: 'You have an incoming video call',
            requireInteraction: true
          });
        } catch (notifError) {
          console.log('Browser notification error (ignored):', notifError);
        }
      }
    }
  };
  const playNotificationSound = () => {
    try {
      // Simple notification beep
      const context = new (window.AudioContext || window.webkitAudioContext)();
      const oscillator = context.createOscillator();
      const gainNode = context.createGain();
      
      oscillator.connect(gainNode);
      gainNode.connect(context.destination);
      
      oscillator.frequency.setValueAtTime(600, context.currentTime);
      oscillator.type = 'sine';
      gainNode.gain.setValueAtTime(0.3, context.currentTime);
      
      oscillator.start(context.currentTime);
      oscillator.stop(context.currentTime + 0.2);
      
      console.log('🔔 Notification sound played');
    } catch (error) {
      console.log('🔔 Notification sound failed (silent mode)');
    }
  };

  const stopRingingSound = () => {
    console.log('🔇 STOPPING ALL RINGTONES AND VIBRATIONS');
    
    // Stop the new ringing interval
    if (window.currentRingingInterval) {
      clearInterval(window.currentRingingInterval);
      window.currentRingingInterval = null;
      console.log('✅ Cleared ringing interval');
    }
    
    // Stop vibration
    if (window.currentVibration) {
      clearInterval(window.currentVibration);
      window.currentVibration = null;
      console.log('✅ Cleared vibration');
    }
    
    // Stop vibration immediately
    if (navigator.vibrate) {
      navigator.vibrate(0);
    }
    
    // Clear any legacy ringing intervals
    if (window.ringingInterval) {
      window.ringingInterval = false;
    }
    
    // Legacy audio cleanup (for backward compatibility)
    if (ringingAudio) {
      if (ringingAudio.stop) {
        ringingAudio.stop(); // Web Audio API
      } else if (ringingAudio.pause) {
        ringingAudio.pause(); // HTML5 Audio
        ringingAudio.currentTime = 0;
      }
      setRingingAudio(null);
    }
    
    setIsRinging(false);
    console.log('🔇 ALL RINGTONES STOPPED');
  };

  const handleAcceptVideoCall = () => {
    stopRingingSound(); // Stop ringing when call is accepted
    if (videoCallInvitation && videoCallInvitation.jitsiUrl) {
      // Enhanced Jitsi URL for provider with automatic participant settings
      const providerJitsiUrl = `${videoCallInvitation.jitsiUrl}&userInfo.displayName=${user.full_name}&config.prejoinPageEnabled=false&config.enableWelcomePage=false&config.startWithVideoMuted=false&config.startWithAudioMuted=false`;
      
      // Universal approach: Works consistently on all devices and browsers
      try {
        const jitsiWindow = window.open(providerJitsiUrl, '_blank', 'width=1200,height=800,scrollbars=yes,resizable=yes,location=yes');
        if (jitsiWindow) {
          jitsiWindow.focus();
          console.log('✅ Video call joined in new window');
        } else {
          // Fallback for popup blockers
          console.log('⚠️ Popup blocked, using location.href fallback');
          window.location.href = providerJitsiUrl;
        }
      } catch (error) {
        console.error('❌ Error opening video call, using fallback:', error);
        window.location.href = providerJitsiUrl;
      }
      
      setShowVideoCallInvitation(false);
      setVideoCallInvitation(null);
    }
  };

  const handleDeclineVideoCall = () => {
    stopRingingSound(); // Stop ringing when call is declined
    setShowVideoCallInvitation(false);
    setVideoCallInvitation(null);
  };

  const fetchAppointments = async () => {
    try {
      console.log('Fetching appointments for provider...');
      const response = await axios.get(`${API}/appointments`);
      console.log('Provider appointments fetched:', response.data.length, 'appointments');
      setAppointments(response.data);
    } catch (error) {
      console.error('Error fetching appointments:', error);
      if (error.response?.status === 401) {
        console.log('Authentication error - user might need to login again');
        // The axios interceptor will handle this
      } else {
        const errorMessage = error.response?.data?.detail || 'Error loading appointments. Please refresh the page.';
        console.error('Provider appointment fetch error:', errorMessage);
      }
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleString();
  };

  const handleCancelAppointment = async (appointmentId) => {
    const confirmed = window.confirm('Are you sure you want to cancel this appointment? This action cannot be undone.');
    if (!confirmed) return;

    try {
      console.log('Attempting to cancel appointment:', appointmentId);
      
      const response = await axios.delete(`${API}/appointments/${appointmentId}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('authToken')}`
        }
      });

      console.log('Cancel appointment response:', response.data);
      
      // Force immediate UI update by filtering out the cancelled appointment
      setAppointments(prevAppointments => {
        const updatedAppointments = prevAppointments.filter(a => a.id !== appointmentId);
        console.log('Updated appointments list:', updatedAppointments.length, 'appointments remaining');
        return updatedAppointments;
      });

      alert('Appointment cancelled successfully');
      
      // Force multiple refresh attempts to ensure UI updates
      setTimeout(async () => {
        console.log('First refresh after appointment cancellation...');
        await fetchAppointments();
      }, 100);
      
      setTimeout(async () => {
        console.log('Second refresh after appointment cancellation...');
        await fetchAppointments();
      }, 1000);
      
    } catch (error) {
      console.error('Error cancelling appointment:', error);
      const errorMessage = error.response?.data?.detail || 'Error cancelling appointment. Please try again.';
      alert(errorMessage);
      // Refresh appointments even on error to check current state
      await fetchAppointments();
    }
  };

  const handleProviderNote = (appointment) => {
    console.log('📝 Provider opening note composer for appointment:', appointment.id);
    setSelectedAppointment(appointment);
    setShowProviderNoteModal(true);
    setProviderNoteText('');
  };

  const handleSendProviderNote = async () => {
    if (!providerNoteText.trim()) {
      alert('Please enter a note before sending.');
      return;
    }

    if (!selectedAppointment) {
      alert('No appointment selected.');
      return;
    }

    try {
      console.log('📤 Provider sending note for appointment:', selectedAppointment.id);
      console.log('📝 Note content:', providerNoteText.trim());

      const response = await axios.post(`${API}/appointments/${selectedAppointment.id}/notes`, {
        note: providerNoteText.trim(),
        note_type: selectedAppointment.appointment_type === 'emergency' ? 'emergency_provider_note' : 'provider_note',
        sender_role: 'provider',
        timestamp: new Date().toISOString()
      });

      console.log('✅ Provider note sent successfully:', response.data);
      
      alert('✅ Note sent successfully to doctor!');
      setShowProviderNoteModal(false);
      setProviderNoteText('');
      setSelectedAppointment(null);
      
      // Force refresh appointments 
      fetchAppointments();
      
    } catch (error) {
      console.error('❌ Error sending provider note:', error);
      console.error('❌ Error details:', error.response?.data);
      alert(`❌ Failed to send note: ${error.response?.data?.detail || error.message}`);
    }
  };

  const handleDeleteAppointment = async (appointmentId, patientName) => {
    const confirmed = window.confirm(`Are you sure you want to delete the appointment for ${patientName}? This action cannot be undone.`);
    if (!confirmed) return;

    try {
      await axios.delete(`${API}/appointments/${appointmentId}`);
      alert('Appointment deleted successfully');
      fetchAppointments();
    } catch (error) {
      console.error('Error deleting appointment:', error);
      alert('Error deleting appointment');
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

  const sendNoteToDoctor = async () => {
    if (!noteText.trim() || !selectedAppointment) return;

    try {
      await axios.post(`${API}/appointments/${selectedAppointment.id}/notes`, {
        note: noteText,
        sender_role: 'provider',
        timestamp: new Date().toISOString()
      });

      alert('Note sent to doctor successfully!');
      setNoteText('');
      
      // Refresh notes
      const notesResponse = await axios.get(`${API}/appointments/${selectedAppointment.id}/notes`);
      setAppointmentNotes(notesResponse.data);
    } catch (error) {
      console.error('Error sending note:', error);
      alert('Error sending note to doctor');
    }
  };

  const handleJoinCall = async (appointmentId) => {
    try {
      // Get Jitsi room for this appointment
      const response = await axios.get(`${API}/video-call/session/${appointmentId}`);
      
      // Extract room name and create a custom Jitsi URL with moderator disabled
      const { jitsi_url } = response.data;
      const roomName = jitsi_url.split('/').pop();
      
      // Create Jitsi URL with config to disable moderator requirement
      const configuredJitsiUrl = `https://meet.jit.si/${roomName}#config.startWithAudioMuted=false&config.startWithVideoMuted=false&config.requireDisplayName=false&config.enableWelcomePage=false&config.prejoinPageEnabled=false&config.enableModeratedDiscussion=false&config.disableModeratorIndicator=true&userInfo.displayName=${user.full_name}`;
      
      console.log(`Opening configured Jitsi meeting: ${configuredJitsiUrl}`);
      
      // Mobile-friendly approach: Use location.href for better mobile compatibility
      if (/Android|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent)) {
        // On mobile devices, open in same tab for better reliability
        window.location.href = configuredJitsiUrl;
      } else {
        // On desktop, try new window first, fallback to same tab
        const newWindow = window.open(configuredJitsiUrl, '_blank', 'width=1200,height=800');
        if (!newWindow || newWindow.closed || typeof newWindow.closed == 'undefined') {
          // Popup blocked, use same tab
          window.location.href = configuredJitsiUrl;
        }
      }
      
    } catch (error) {
      console.error('Error joining video call:', error);
      alert('Error joining video call. Please try again.');
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'pending': return 'status-pending';
      case 'accepted': return 'status-accepted';
      case 'completed': return 'status-completed';
      case 'cancelled': return 'bg-red-100 text-red-800';
      default: return 'status-pending';
    }
  };

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
              <h1 className="nav-brand text-green-700">Greenstar Telehealth</h1>
              <p className="text-sm text-gray-600">Provider Dashboard</p>
            </div>
          </div>
          
          <div className="flex items-center space-x-4">
            <div className="text-right">
              <p className="font-semibold text-gray-900">{user.full_name}</p>
              <p className="text-sm text-gray-600">{user.district}</p>
            </div>
            {/* Refresh button removed as requested */}
            
            <button
              onClick={() => setShowNotificationPanel(true)}
              className="flex items-center space-x-2 px-3 py-2 text-green-600 hover:bg-green-50 rounded-lg transition-colors relative"
              title="Notifications"
            >
              <Bell className="w-4 h-4" />
              <span className="hidden sm:inline">Notifications</span>
              {unreadNotifications > 0 && (
                <span className="absolute -top-1 -right-1 bg-red-500 text-white text-xs font-bold px-1 py-0.5 rounded-full min-w-[16px] h-4 flex items-center justify-center">
                  {unreadNotifications}
                </span>
              )}
            </button>
            <button
              onClick={() => setShowNotificationSettings(true)}
              className="flex items-center space-x-2 px-3 py-2 text-gray-600 hover:bg-gray-50 rounded-lg transition-colors"
              title="Notification Settings"
            >
              <Bell className="w-4 h-4" />
              <span className="hidden sm:inline">Settings</span>
            </button>
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
        {/* Quick Actions */}
        <div className="dashboard-grid mb-8">
          <div className="glass-card">
            <h3 className="text-xl font-semibold text-gray-900 mb-4 flex items-center">
              <Plus className="w-6 h-6 mr-2 text-green-600" />
              New Appointment
            </h3>
            <p className="text-gray-600 mb-6">
              Create a new appointment for patient consultation
            </p>
            <div className="flex flex-col sm:flex-row gap-3">
              <button
                onClick={() => navigate('/patient-form?type=emergency')}
                className="btn-emergency flex-1 flex items-center justify-center space-x-2"
              >
                <AlertTriangle className="w-5 h-5" />
                <span>Emergency</span>
              </button>
              <button
                onClick={() => navigate('/patient-form?type=non_emergency')}
                className="btn-secondary flex-1 flex items-center justify-center space-x-2"
              >
                <Clock className="w-5 h-5" />
                <span>Non-Emergency</span>
              </button>
            </div>
          </div>

          <div className="glass-card">
            <h3 className="text-xl font-semibold text-gray-900 mb-4 flex items-center">
              <Calendar className="w-6 h-6 mr-2 text-green-600" />
              Today's Summary
            </h3>
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <span className="text-gray-600">Total Appointments</span>
                <span className="font-semibold text-lg">{appointments.length}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-gray-600">Emergency Calls</span>
                <span className="font-semibold text-lg text-red-600">
                  {appointments.filter(apt => apt.appointment_type === 'emergency').length}
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-gray-600">Completed</span>
                <span className="font-semibold text-lg text-green-600">
                  {appointments.filter(apt => apt.status === 'completed').length}
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Appointments List */}
        <div className="glass-card">
          <h2 className="text-2xl font-bold text-gray-900 mb-6 flex items-center">
            <Phone className="w-7 h-7 mr-3 text-green-600" />
            My Appointments
          </h2>

          {loading ? (
            <div className="flex items-center justify-center py-12">
              <div className="loading-spinner"></div>
              <span className="ml-3 text-gray-600">Loading appointments...</span>
            </div>
          ) : appointments.length === 0 ? (
            <div className="text-center py-12">
              <Calendar className="w-16 h-16 text-gray-300 mx-auto mb-4" />
              <p className="text-gray-500 text-lg">No appointments found</p>
              <p className="text-gray-400">Create your first appointment to get started</p>
            </div>
          ) : (
            <div className="space-y-4">
              {appointments.map((appointment) => (
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
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                          appointment.appointment_type === 'emergency' 
                            ? 'bg-red-100 text-red-800' 
                            : 'bg-green-100 text-green-800'
                        }`}>
                          {appointment.appointment_type === 'emergency' ? 'EMERGENCY' : 'ROUTINE'}
                        </span>
                      </div>
                      
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
                        <div>
                          <p className="text-gray-600">Patient Info</p>
                          <p className="font-medium">
                            {appointment.patient?.age}y, {appointment.patient?.gender}
                          </p>
                        </div>
                        <div>
                          <p className="text-gray-600">Patient History</p>
                          <p className="font-medium">
                            {appointment.patient?.history}
                          </p>
                        </div>
                        <div>
                          <p className="text-gray-600">Area of Consultation</p>
                          <p className="font-medium">
                            {appointment.patient?.area_of_consultation}
                          </p>
                        </div>
                        <div>
                          <p className="text-gray-600">Created</p>
                          <p className="font-medium">
                            {formatDate(appointment.created_at)}
                          </p>
                        </div>
                      </div>

                      {appointment.doctor && (
                        <div className="mt-3 p-3 bg-green-50 rounded-lg">
                          <p className="text-sm text-gray-600">Assigned Doctor</p>
                          <p className="font-medium text-green-900">
                            Dr. {appointment.doctor.full_name}
                          </p>
                          {appointment.doctor.specialty && (
                            <p className="text-sm text-green-700">
                              {appointment.doctor.specialty}
                            </p>
                          )}
                        </div>
                      )}
                    </div>

                    {/* Provider Actions - Simple and clean */}
                    <div className="ml-4 flex flex-col space-y-2">
                      {/* Emergency appointments: Show Video Call status */}
                      {appointment.appointment_type === 'emergency' && appointment.status === 'accepted' && (
                        <div className="bg-green-50 border border-green-200 rounded-lg p-3 text-center">
                          <Phone className="w-5 h-5 text-green-600 mx-auto mb-2" />
                          <p className="text-sm text-green-800 font-medium mb-1">Ready for Video Call</p>
                          <p className="text-xs text-green-600">Waiting for Dr. {appointment.doctor?.full_name || 'doctor'} to call</p>
                        </div>
                      )}
                      
                      {/* Send Note to Doctor button - Always available */}
                      <button
                        onClick={() => handleProviderNote(appointment)}
                        className="bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded-lg flex items-center space-x-2 transition-colors"
                      >
                        <MessageSquare className="w-4 h-4" />
                        <span>Send Note to Doctor</span>
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

      {/* Provider Appointment Details Modal */}
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

              {/* Doctor & Appointment Info */}
              <div className="space-y-4">
                {selectedAppointment.doctor ? (
                  <div className="glass-card">
                    <h4 className="text-lg font-semibold text-gray-900 mb-4">Assigned Doctor</h4>
                    <div className="space-y-3">
                      <div>
                        <p className="text-sm text-gray-600">Name</p>
                        <p className="font-medium">Dr. {selectedAppointment.doctor?.full_name}</p>
                      </div>
                      {selectedAppointment.doctor?.specialty && (
                        <div>
                          <p className="text-sm text-gray-600">Specialty</p>
                          <p className="font-medium">{selectedAppointment.doctor.specialty}</p>
                        </div>
                      )}
                      <div>
                        <p className="text-sm text-gray-600">Phone</p>
                        <p className="font-medium">{selectedAppointment.doctor?.phone}</p>
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="glass-card">
                    <h4 className="text-lg font-semibold text-gray-900 mb-4">Doctor Assignment</h4>
                    <p className="text-gray-600">No doctor assigned yet. Waiting for a doctor to accept this appointment.</p>
                  </div>
                )}

                <div className="glass-card">
                  <h4 className="text-lg font-semibold text-gray-900 mb-4">Appointment Status</h4>
                  <div className="space-y-3">
                    <div className="flex items-center space-x-3">
                      <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                        selectedAppointment.appointment_type === 'emergency' 
                          ? 'bg-red-100 text-red-800' 
                          : 'bg-green-100 text-green-800'
                      }`}>
                        {selectedAppointment.appointment_type === 'emergency' ? 'EMERGENCY' : 'NON-EMERGENCY'}
                      </span>
                      <span className={`px-3 py-1 rounded-full text-sm font-medium ${
                        selectedAppointment.status === 'pending' ? 'bg-yellow-100 text-yellow-800' :
                        selectedAppointment.status === 'accepted' ? 'bg-green-100 text-green-800' :
                        selectedAppointment.status === 'completed' ? 'bg-blue-100 text-blue-800' :
                        'bg-red-100 text-red-800'
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
              <h4 className="text-lg font-semibold text-gray-900 mb-4">Communication with Doctor</h4>
              
              {/* Existing Notes */}
              <div className="space-y-3 mb-4 max-h-40 overflow-y-auto">
                {appointmentNotes.length > 0 ? (
                  appointmentNotes.map((note, index) => (
                    <div key={index} className={`p-3 rounded-lg ${
                      note.sender_role === 'doctor' ? 'bg-blue-50 mr-8' : 'bg-green-50 ml-8'
                    }`}>
                      <div className="flex justify-between items-start mb-1">
                        <span className="font-medium text-sm">
                          {note.sender_role === 'doctor' ? 'Dr.' : 'Provider'} {note.sender_name}
                        </span>
                        <span className="text-xs text-gray-500">
                          {new Date(note.timestamp).toLocaleString()}
                        </span>
                      </div>
                      <p className="text-sm">{note.note}</p>
                    </div>
                  ))
                ) : (
                  <p className="text-gray-500 text-center py-4">No communication yet</p>
                )}
              </div>

              {/* Add New Note */}
              {selectedAppointment.doctor && (
                <div className="bg-green-50 p-4 rounded-lg">
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Send Message to Doctor
                  </label>
                  <div className="flex space-x-3">
                    <textarea
                      value={noteText}
                      onChange={(e) => setNoteText(e.target.value)}
                      className="flex-1 form-input"
                      rows={3}
                      placeholder="Type your message to the doctor..."
                    />
                    <button
                      onClick={sendNoteToDoctor}
                      disabled={!noteText.trim()}
                      className="btn-primary flex items-center space-x-2 self-start disabled:opacity-50"
                    >
                      <Send className="w-4 h-4" />
                      <span>Send</span>
                    </button>
                  </div>
                </div>
              )}
            </div>

            {/* Action Buttons - Simplified */}
            <div className="flex justify-end space-x-4 mt-6 pt-6 border-t">
              {/* Send Note to Doctor button */}
              <button
                onClick={() => {
                  setShowAppointmentModal(false);
                  handleProviderNote(selectedAppointment);
                }}
                className="bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded-lg flex items-center space-x-2 transition-colors"
              >
                <MessageSquare className="w-4 h-4" />
                <span>Send Note to Doctor</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Enhanced Video Call Invitation with Appointment Details */}
      {showVideoCallInvitation && videoCallInvitation && (
        <div className="fixed inset-0 bg-black bg-opacity-80 flex items-center justify-center z-50">
          <div className="glass-card max-w-lg w-full mx-4 max-h-[90vh] overflow-y-auto">
            <div className="p-8">
              
              {/* Call Header */}
              <div className="text-center mb-6">
                <div className={`w-24 h-24 mx-auto rounded-full bg-gradient-to-r ${
                  videoCallInvitation.appointmentType === 'emergency' 
                    ? 'from-red-500 to-red-600' 
                    : 'from-green-500 to-green-600'
                } flex items-center justify-center ${isRinging ? 'animate-pulse' : ''} shadow-lg`}>
                  <Phone className="w-12 h-12 text-white animate-bounce" />
                </div>
                
                <h2 className="text-3xl font-bold text-gray-900 mt-4">
                  {isRinging ? 'Incoming Call...' : 'Video Call Invitation'}
                </h2>
                
                {isRinging && (
                  <p className="text-sm text-gray-500 animate-pulse mt-2">
                    📞 Ring Ring... Ring Ring...
                  </p>
                )}
              </div>

              {/* Appointment Type Badge */}
              <div className="text-center mb-6">
                <span className={`inline-flex items-center px-4 py-2 rounded-full text-sm font-semibold ${
                  videoCallInvitation.appointmentType === 'emergency'
                    ? 'bg-red-100 text-red-800 border border-red-200'
                    : 'bg-blue-100 text-blue-800 border border-blue-200'
                }`}>
                  {videoCallInvitation.appointmentType === 'emergency' ? '🚨 EMERGENCY' : '📅 REGULAR'} CONSULTATION
                </span>
              </div>

              {/* Caller Information */}
              <div className="bg-gray-50 rounded-lg p-4 mb-6">
                <h3 className="font-semibold text-gray-900 mb-2">📞 Caller</h3>
                <div className="flex items-center space-x-3">
                  <div className="w-12 h-12 bg-blue-500 rounded-full flex items-center justify-center">
                    <User className="w-6 h-6 text-white" />
                  </div>
                  <div>
                    <p className="font-semibold text-lg text-gray-900">
                      {videoCallInvitation.callerRole === 'doctor' ? 'Dr. ' : ''}{videoCallInvitation.callerName}
                    </p>
                    <p className="text-sm text-gray-600 capitalize">
                      {videoCallInvitation.callerRole || 'Healthcare Provider'}
                    </p>
                  </div>
                </div>
              </div>

              {/* Patient Information */}
              <div className="bg-gradient-to-r from-blue-50 to-purple-50 rounded-lg p-4 mb-6">
                <h3 className="font-semibold text-gray-900 mb-3">👤 Patient Information</h3>
                
                <div className="grid grid-cols-2 gap-4 mb-3">
                  <div>
                    <label className="text-xs font-medium text-gray-500 uppercase tracking-wide">Name</label>
                    <p className="text-sm font-semibold text-gray-900">{videoCallInvitation.patient.name}</p>
                  </div>
                  <div>
                    <label className="text-xs font-medium text-gray-500 uppercase tracking-wide">Age</label>
                    <p className="text-sm font-semibold text-gray-900">{videoCallInvitation.patient.age} years</p>
                  </div>
                </div>
                
                <div className="grid grid-cols-2 gap-4 mb-3">
                  <div>
                    <label className="text-xs font-medium text-gray-500 uppercase tracking-wide">Gender</label>
                    <p className="text-sm font-semibold text-gray-900 capitalize">{videoCallInvitation.patient.gender}</p>
                  </div>
                  <div>
                    <label className="text-xs font-medium text-gray-500 uppercase tracking-wide">Type</label>
                    <p className="text-sm font-semibold text-gray-900 capitalize">
                      {videoCallInvitation.appointmentType.replace('_', ' ')}
                    </p>
                  </div>
                </div>

                <div>
                  <label className="text-xs font-medium text-gray-500 uppercase tracking-wide">Patient History</label>
                  <p className="text-sm text-gray-900 bg-white rounded p-2 mt-1">
                    {videoCallInvitation.patient.history}
                  </p>
                </div>
                <div>
                  <label className="text-xs font-medium text-gray-500 uppercase tracking-wide">Area of Consultation</label>
                  <p className="text-sm text-gray-900 bg-white rounded p-2 mt-1">
                    {videoCallInvitation.patient.area_of_consultation}
                  </p>
                </div>

                {/* Patient Vitals (if available) */}
                {videoCallInvitation.patient.vitals && Object.keys(videoCallInvitation.patient.vitals).length > 0 && (
                  <div className="mt-3 pt-3 border-t border-gray-200">
                    <label className="text-xs font-medium text-gray-500 uppercase tracking-wide">Recent Vitals</label>
                    <div className="grid grid-cols-2 gap-2 mt-2">
                      {videoCallInvitation.patient.vitals.blood_pressure && (
                        <div className="bg-white rounded p-2">
                          <span className="text-xs text-gray-500">BP:</span>
                          <span className="text-sm font-medium ml-1">{videoCallInvitation.patient.vitals.blood_pressure}</span>
                        </div>
                      )}
                      {videoCallInvitation.patient.vitals.heart_rate && (
                        <div className="bg-white rounded p-2">
                          <span className="text-xs text-gray-500">HR:</span>
                          <span className="text-sm font-medium ml-1">{videoCallInvitation.patient.vitals.heart_rate} bpm</span>
                        </div>
                      )}
                      {videoCallInvitation.patient.vitals.temperature && (
                        <div className="bg-white rounded p-2">
                          <span className="text-xs text-gray-500">Temp:</span>
                          <span className="text-sm font-medium ml-1">{videoCallInvitation.patient.vitals.temperature}°C</span>
                        </div>
                      )}
                      {videoCallInvitation.patient.vitals.oxygen_saturation && (
                        <div className="bg-white rounded p-2">
                          <span className="text-xs text-gray-500">O2:</span>
                          <span className="text-sm font-medium ml-1">{videoCallInvitation.patient.vitals.oxygen_saturation}%</span>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>

              {/* Call Action Buttons */}
              <div className="flex space-x-4">
                <button
                  onClick={handleAcceptVideoCall}
                  className={`flex-1 ${
                    videoCallInvitation.appointmentType === 'emergency' 
                      ? 'bg-red-500 hover:bg-red-600' 
                      : 'bg-green-500 hover:bg-green-600'
                  } text-white px-8 py-4 rounded-xl font-semibold flex items-center justify-center space-x-3 transition-all transform hover:scale-105 shadow-lg`}
                >
                  <Phone className="w-6 h-6" />
                  <span>Answer Call</span>
                </button>
                
                <button
                  onClick={handleDeclineVideoCall}
                  className="flex-1 bg-gray-500 hover:bg-gray-600 text-white px-8 py-4 rounded-xl font-semibold flex items-center justify-center space-x-3 transition-all transform hover:scale-105 shadow-lg"
                >
                  <PhoneOff className="w-6 h-6" />
                  <span>Decline</span>
                </button>
              </div>
              
              {/* Timer */}
              <div className="text-center mt-4">
                <p className="text-xs text-gray-400">
                  {videoCallInvitation.appointmentType === 'emergency' ? 'Emergency call' : 'Call'} will auto-dismiss in 30 seconds
                </p>
              </div>
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

      {/* Provider Note Modal */}
      {showProviderNoteModal && selectedAppointment && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="glass-card max-w-lg w-full mx-4">
            <div className="flex items-center justify-between mb-6">
              <h3 className="text-xl font-bold text-gray-900">Send Note to Doctor</h3>
              <button
                onClick={() => {
                  setShowProviderNoteModal(false);
                  setProviderNoteText('');
                  setSelectedAppointment(null);
                }}
                className="text-gray-500 hover:text-gray-700 text-xl"
              >
                ×
              </button>
            </div>

            <div className="mb-4">
              <p className="text-sm text-gray-600 mb-2">
                <strong>Patient:</strong> {selectedAppointment.patient?.name}
              </p>
              <p className="text-sm text-gray-600 mb-4">
                <strong>Appointment Type:</strong> {selectedAppointment.appointment_type}
              </p>
            </div>

            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Your Note to Doctor
              </label>
              <textarea
                value={providerNoteText}
                onChange={(e) => setProviderNoteText(e.target.value)}
                className="w-full form-input"
                rows={6}
                placeholder="Enter your note for the doctor about this patient..."
              />
            </div>

            <div className="flex justify-end space-x-3">
              <button
                onClick={() => {
                  setShowProviderNoteModal(false);
                  setProviderNoteText('');
                  setSelectedAppointment(null);
                }}
                className="btn-secondary"
              >
                Cancel
              </button>
              <button
                onClick={handleSendProviderNote}
                disabled={!providerNoteText.trim()}
                className="btn-primary flex items-center space-x-2 disabled:opacity-50"
              >
                <Send className="w-4 h-4" />
                <span>Send Note</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Provider Note Modal */}
      {showProviderNoteModal && selectedAppointment && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg max-w-md w-full max-h-[80vh] overflow-y-auto">
            <div className="p-6">
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-xl font-bold text-gray-900">
                  📝 Send Note to Doctor
                </h2>
                <button
                  onClick={() => {
                    setShowProviderNoteModal(false);
                    setProviderNoteText('');
                    setSelectedAppointment(null);
                  }}
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
                  <strong>Doctor:</strong> {selectedAppointment.doctor_name || 'Not yet assigned'}
                </p>
              </div>

              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Your Note/Message to Doctor:
                </label>
                <textarea
                  value={providerNoteText}
                  onChange={(e) => setProviderNoteText(e.target.value)}
                  rows={6}
                  className="w-full p-3 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="Enter your notes, questions, or updates about the patient for the doctor..."
                  maxLength={1000}
                />
                <p className="text-xs text-gray-500 mt-1">
                  {providerNoteText.length}/1000 characters
                </p>
              </div>

              <div className="flex space-x-3">
                <button
                  onClick={handleSendProviderNote}
                  disabled={!providerNoteText.trim()}
                  className="flex-1 bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  📤 Send Note
                </button>
                <button
                  onClick={() => {
                    setShowProviderNoteModal(false);
                    setProviderNoteText('');
                    setSelectedAppointment(null);
                  }}
                  className="flex-1 bg-gray-300 text-gray-700 px-4 py-2 rounded-lg hover:bg-gray-400 focus:outline-none focus:ring-2 focus:ring-gray-500"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Notification Settings Modal */}
      <NotificationSettings 
        isOpen={showNotificationSettings}
        onClose={() => setShowNotificationSettings(false)}
      />
    </div>
  );
};

export default Dashboard;