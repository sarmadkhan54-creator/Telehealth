import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Plus, Clock, AlertTriangle, User, LogOut, Calendar, Phone, PhoneOff, X, Eye, Send, Bell } from 'lucide-react';
import NotificationSettings from './NotificationSettings';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const Dashboard = ({ user, onLogout }) => {
  const [appointments, setAppointments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedAppointment, setSelectedAppointment] = useState(null);
  const [showAppointmentModal, setShowAppointmentModal] = useState(false);
  const [noteText, setNoteText] = useState('');
  const [appointmentNotes, setAppointmentNotes] = useState([]);
  const [notifications, setNotifications] = useState([]);
  const [showVideoCallInvitation, setShowVideoCallInvitation] = useState(false);
  const [videoCallInvitation, setVideoCallInvitation] = useState(null);
  const [isRinging, setIsRinging] = useState(false);
  const [ringingAudio, setRingingAudio] = useState(null);
  const [showNotificationSettings, setShowNotificationSettings] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    fetchAppointments();
    setupWebSocket();
    
    // Auto-refresh appointments every 30 seconds
    const refreshInterval = setInterval(fetchAppointments, 30000); // Refresh every 30 seconds
    
    // Request notification permissions on first interaction
    const requestPermissionsOnInteraction = async () => {
      try {
        // Request notification permission
        if ('Notification' in window && Notification.permission === 'default') {
          const permission = await Notification.requestPermission();
          console.log('📱 Notification permission requested:', permission);
          
          if (permission === 'granted') {
            // Initialize push notifications after permission granted
            const { pushNotificationManager } = await import('../utils/pushNotifications');
            await pushNotificationManager.initialize(true);
            console.log('✅ Push notifications initialized after permission grant');
          }
        }
        
        // Test audio context (requires user interaction)
        if (window.AudioContext || window.webkitAudioContext) {
          const audioContext = new (window.AudioContext || window.webkitAudioContext)();
          if (audioContext.state === 'suspended') {
            await audioContext.resume();
            console.log('✅ Audio context resumed after user interaction');
          }
        }
      } catch (error) {
        console.error('Error requesting permissions:', error);
      }
    };
    
    // Add click listener to enable permissions on first interaction
    const handleFirstInteraction = () => {
      requestPermissionsOnInteraction();
      document.removeEventListener('click', handleFirstInteraction);
      document.removeEventListener('touchstart', handleFirstInteraction);
    };
    
    document.addEventListener('click', handleFirstInteraction);
    document.addEventListener('touchstart', handleFirstInteraction);
    
    return () => {
      clearInterval(refreshInterval);
      document.removeEventListener('click', handleFirstInteraction);
      document.removeEventListener('touchstart', handleFirstInteraction);
    };
  }, []);

  const setupWebSocket = () => {
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
    
    console.log(`🔌 Connecting to WebSocket: ${wsUrl}`);
    
    try {
      const ws = new WebSocket(wsUrl);
      
      ws.onopen = () => {
        console.log('✅ WebSocket connected successfully');
      };
    
      ws.onmessage = (event) => {
        try {
          const notification = JSON.parse(event.data);
          console.log('📨 Received WebSocket notification:', notification);
          
          // Auto-refresh appointments when receiving notifications
          if (notification.type === 'emergency_appointment' || 
              notification.type === 'appointment_accepted' || 
              notification.type === 'appointment_updated' ||
              notification.type === 'video_call_invitation') {
            fetchAppointments(); // Refresh appointments list
          }
          
          // Handle Jitsi video call invitations
          if (notification.type === 'jitsi_call_invitation') {
            console.log('📞 Received video call invitation');
            
            // Play ringing sound
            playRingingSound();
            
            // Show video call invitation popup with Jitsi URL
            setVideoCallInvitation({
              jitsiUrl: notification.jitsi_url,
              roomName: notification.room_name,
              callerName: notification.caller,
              callerRole: notification.caller_role,
              appointmentId: notification.appointment_id,
              appointmentType: notification.appointment_type,
              patient: notification.patient || {
                name: "Unknown Patient",
                age: "Unknown",
                gender: "Unknown", 
                consultation_reason: "General consultation",
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
            
            // Send browser notification if permission granted
            if (Notification.permission === 'granted') {
              const browserNotification = new Notification('📞 Incoming Video Call', {
                body: `${notification.caller} is inviting you to a video consultation`,
                icon: '/icons/icon-192x192.png',
                badge: '/icons/badge-72x72.png',
                tag: 'video-call-invitation',
                requireInteraction: true,
                actions: [
                  { action: 'answer', title: 'Answer' },
                  { action: 'decline', title: 'Decline' }
                ]
              });
              
              browserNotification.onclick = () => {
                handleAcceptVideoCall();
                browserNotification.close();
              };
            }
          }
          
          // Handle other notification types
          if (Notification.permission === 'granted') {
            if (notification.type === 'appointment_accepted') {
              new Notification('✅ Appointment Accepted', {
                body: `Doctor accepted your appointment for ${notification.patient_name}`,
                icon: '/icons/icon-192x192.png'
              });
            } else if (notification.type === 'emergency_appointment') {
              new Notification('🚨 Emergency Appointment', {
                body: `New emergency appointment: ${notification.patient_name}`,
                icon: '/icons/icon-192x192.png',
                requireInteraction: true
              });
            }
          }
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };

      ws.onerror = (error) => {
        console.error('❌ WebSocket error:', error);
      };

      ws.onclose = (event) => {
        console.log('🔌 WebSocket disconnected, attempting to reconnect in 5 seconds...');
        console.log('Close event:', event.code, event.reason);
        
        // Clear existing timeout if any
        if (reconnectTimeout) {
          clearTimeout(reconnectTimeout);
        }
        
        // Try to reconnect after 5 seconds
        const reconnectTimeout = setTimeout(() => {
          console.log('🔄 Attempting WebSocket reconnection...');
          setupWebSocket();
        }, 5000);
      };

      // Request notification permission for mobile
      if ('Notification' in window && Notification.permission === 'default') {
        Notification.requestPermission().then(permission => {
          console.log('📱 Notification permission:', permission);
        });
      }

      return () => ws.close();
      
    } catch (error) {
      console.error('❌ Error setting up WebSocket:', error);
      // Retry after 5 seconds
      setTimeout(setupWebSocket, 5000);
    }
  };

  const playRingingSound = async () => {
    try {
      // Ensure audio context is available and running
      let audioContext;
      try {
        audioContext = new (window.AudioContext || window.webkitAudioContext)();
        if (audioContext.state === 'suspended') {
          await audioContext.resume();
          console.log('✅ Audio context resumed for ringing sound');
        }
      } catch (contextError) {
        console.error('Audio context creation failed:', contextError);
        throw contextError;
      }
      
      // Create a continuous ringing sound like a real phone
      let isRingingActive = true;
      
      const ringingInterval = setInterval(() => {
        if (!isRingingActive) return;
        
        const createRingTone = (frequency, startTime, duration) => {
          const oscillator = audioContext.createOscillator();
          const gainNode = audioContext.createGain();
          
          oscillator.connect(gainNode);
          gainNode.connect(audioContext.destination);
          
          oscillator.type = 'sine';
          oscillator.frequency.value = frequency;
          
          gainNode.gain.setValueAtTime(0, startTime);
          gainNode.gain.linearRampToValueAtTime(0.2, startTime + 0.05); // Increased volume
          gainNode.gain.exponentialRampToValueAtTime(0.01, startTime + duration);
          
          oscillator.start(startTime);
          oscillator.stop(startTime + duration);
        };
        
        // Create ring sequence (ring-ring pattern)
        const now = audioContext.currentTime;
        createRingTone(800, now, 0.3);      // First ring
        createRingTone(800, now + 0.4, 0.3); // Second ring
        
      }, 2000); // Ring every 2 seconds
      
      // Stop ringing function
      const stopRinging = () => {
        isRingingActive = false;
        clearInterval(ringingInterval);
        setIsRinging(false);
      };
      
      // Store the stop function
      setRingingAudio({ stop: stopRinging });
      setIsRinging(true);
      
      console.log('📞 Started phone ringing sound with enhanced audio');
      return stopRinging;
      
    } catch (error) {
      console.error('Web Audio API failed, trying HTML5 Audio fallback:', error);
      
      // Enhanced fallback to HTML5 Audio with looping
      try {
        // Create a better ring tone data URL
        const createRingToneUrl = () => {
          const audioContext = new (window.AudioContext || window.webkitAudioContext)();
          const sampleRate = audioContext.sampleRate;
          const duration = 0.3;
          const frequency = 800;
          
          const samples = sampleRate * duration;
          const buffer = new Float32Array(samples);
          
          for (let i = 0; i < samples; i++) {
            const t = i / sampleRate;
            buffer[i] = Math.sin(2 * Math.PI * frequency * t) * 0.3 * Math.exp(-t * 3);
          }
          
          return buffer;
        };
        
        // Use a simple audio element with looping
        const audio = new Audio();
        audio.loop = true;
        audio.volume = 0.5;
        
        // Create a simple beep sound data URL
        const beepData = 'data:audio/wav;base64,UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqFbF1fdJivrJBhNjVgodDbq2EcBj+a2/LDciUFLIHO8tiJNwgZaLvt559NEAxQp+PwtmMcBjiR1/LMeSwFJHfH8N2QQAoUXrTp6qNVFApGn+DyvGYfCSSLzfDVgjMGHW7A7+OZURE';
        audio.src = beepData;
        
        const playPromise = audio.play();
        
        if (playPromise !== undefined) {
          playPromise.then(() => {
            console.log('📞 Fallback ringing sound playing (HTML5 Audio)');
            setRingingAudio(audio);
            setIsRinging(true);
          }).catch(fallbackError => {
            console.error('All audio playback methods failed:', fallbackError);
            
            // Last resort: Browser notification with requireInteraction
            if ('Notification' in window && Notification.permission === 'granted') {
              const notification = new Notification('📞 Incoming Video Call', {
                body: 'You have an incoming video call. Click to answer.',
                requireInteraction: true,
                tag: 'video-call-backup'
              });
              
              notification.onclick = () => {
                // Handle call acceptance here if needed
                notification.close();
              };
              
              console.log('📞 Using notification as audio fallback');
            }
          });
        }
        
      } catch (fallbackError) {
        console.error('All ringing sound methods failed:', fallbackError);
        
        // Final fallback: Just show visual notification
        setIsRinging(true);
        console.log('📞 Using visual-only notification (no audio available)');
      }
    }
  };
  const stopRingingSound = () => {
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
    console.log('📞 Stopped ringing sound');
  };

  const handleAcceptVideoCall = () => {
    stopRingingSound(); // Stop ringing when call is accepted
    if (videoCallInvitation && videoCallInvitation.jitsiUrl) {
      // Mobile-friendly approach for accepting video calls
      if (/Android|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent)) {
        // On mobile devices, open in same tab for better reliability
        window.location.href = videoCallInvitation.jitsiUrl;
      } else {
        // On desktop, try new window first, fallback to same tab
        const newWindow = window.open(videoCallInvitation.jitsiUrl, '_blank', 'width=1200,height=800');
        if (!newWindow || newWindow.closed || typeof newWindow.closed == 'undefined') {
          // Popup blocked, use same tab
          window.location.href = videoCallInvitation.jitsiUrl;
        }
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
      const response = await axios.get(`${API}/appointments`);
      setAppointments(response.data);
    } catch (error) {
      console.error('Error fetching appointments:', error);
    } finally {
      setLoading(false);
    }
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleString();
  };

  const handleCancelAppointment = async (appointmentId, patientName) => {
    const confirmed = window.confirm(`Are you sure you want to cancel the appointment for ${patientName}?`);
    if (!confirmed) return;

    try {
      await axios.put(`${API}/appointments/${appointmentId}`, {
        status: 'cancelled'
      });
      alert('Appointment cancelled successfully');
      fetchAppointments();
    } catch (error) {
      console.error('Error cancelling appointment:', error);
      alert('Error cancelling appointment');
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
      const { jitsi_url } = response.data;
      
      console.log(`Opening Jitsi meeting: ${jitsi_url}`);
      
      // Mobile-friendly approach: Use location.href for better mobile compatibility
      if (/Android|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent)) {
        // On mobile devices, open in same tab for better reliability
        window.location.href = jitsi_url;
      } else {
        // On desktop, try new window first, fallback to same tab
        const newWindow = window.open(jitsi_url, '_blank', 'width=1200,height=800');
        if (!newWindow || newWindow.closed || typeof newWindow.closed == 'undefined') {
          // Popup blocked, use same tab
          window.location.href = jitsi_url;
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
            <button
              onClick={() => setShowNotificationSettings(true)}
              className="flex items-center space-x-2 px-3 py-2 text-green-600 hover:bg-green-50 rounded-lg transition-colors"
              title="Notification Settings"
            >
              <Bell className="w-4 h-4" />
              <span className="hidden sm:inline">Notifications</span>
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
                          <p className="text-gray-600">Consultation Reason</p>
                          <p className="font-medium">
                            {appointment.patient?.consultation_reason}
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

                    {/* Provider Actions */}
                    <div className="ml-4 flex flex-col space-y-2">
                      {appointment.status === 'accepted' && (
                        <button
                          onClick={() => handleJoinCall(appointment.id)}
                          className="btn-primary flex items-center space-x-2"
                        >
                          <Phone className="w-4 h-4" />
                          <span>Join Call</span>
                        </button>
                      )}

                      <button
                        onClick={() => viewAppointmentDetails(appointment)}
                        className="btn-secondary flex items-center space-x-2"
                      >
                        <Eye className="w-4 h-4" />
                        <span>View Details</span>
                      </button>

                      {(appointment.status === 'pending' || appointment.status === 'accepted') && (
                        <>
                          <button
                            onClick={() => handleCancelAppointment(appointment.id, appointment.patient?.name)}
                            className="btn-secondary flex items-center space-x-2 text-orange-600 hover:text-orange-800"
                          >
                            <X className="w-4 h-4" />
                            <span>Cancel</span>
                          </button>
                          
                          {appointment.status === 'pending' && (
                            <button
                              onClick={() => handleDeleteAppointment(appointment.id, appointment.patient?.name)}
                              className="btn-secondary flex items-center space-x-2 text-red-600 hover:text-red-800"
                            >
                              <X className="w-4 h-4" />
                              <span>Delete</span>
                            </button>
                          )}
                        </>
                      )}
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
                    <p className="text-sm text-gray-600">Consultation Reason</p>
                    <p className="font-medium">{selectedAppointment.patient?.consultation_reason}</p>
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

            {/* Action Buttons */}
            <div className="flex justify-end space-x-4 mt-6 pt-6 border-t">
              {selectedAppointment.status === 'accepted' && (
                <button
                  onClick={() => {
                    handleJoinCall(selectedAppointment.id);
                    setShowAppointmentModal(false);
                  }}
                  className="btn-primary flex items-center space-x-2"
                >
                  <Phone className="w-4 h-4" />
                  <span>Join Video Call</span>
                </button>
              )}
              
              {(selectedAppointment.status === 'pending' || selectedAppointment.status === 'accepted') && (
                <button
                  onClick={() => {
                    handleCancelAppointment(selectedAppointment.id, selectedAppointment.patient?.name);
                    setShowAppointmentModal(false);
                  }}
                  className="btn-secondary flex items-center space-x-2 text-orange-600 hover:text-orange-800"
                >
                  <X className="w-4 h-4" />
                  <span>Cancel Appointment</span>
                </button>
              )}
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
                  <label className="text-xs font-medium text-gray-500 uppercase tracking-wide">Consultation Reason</label>
                  <p className="text-sm text-gray-900 bg-white rounded p-2 mt-1">
                    {videoCallInvitation.patient.consultation_reason}
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
      
      {/* Notification Settings Modal */}
      <NotificationSettings 
        isOpen={showNotificationSettings}
        onClose={() => setShowNotificationSettings(false)}
      />
    </div>
  );
};

export default Dashboard;