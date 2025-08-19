import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Plus, Clock, AlertTriangle, User, LogOut, Calendar, Phone, X, Eye, Send } from 'lucide-react';

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
  const navigate = useNavigate();

  useEffect(() => {
    fetchAppointments();
    setupWebSocket();
    
    // Set up auto-refresh interval as fallback
    const refreshInterval = setInterval(fetchAppointments, 30000); // Refresh every 30 seconds
    
    return () => {
      clearInterval(refreshInterval);
    };
  }, []);

  const setupWebSocket = () => {
    const wsUrl = `${BACKEND_URL.replace('https:', 'wss:').replace('http:', 'ws:')}/api/ws/${user.id}`;
    const ws = new WebSocket(wsUrl);
    
    ws.onmessage = (event) => {
      const notification = JSON.parse(event.data);
      
      // Auto-refresh appointments when receiving notifications
      if (notification.type === 'emergency_appointment' || 
          notification.type === 'appointment_accepted' || 
          notification.type === 'appointment_updated' ||
          notification.type === 'video_call_invitation') {
        fetchAppointments(); // Refresh appointments list
      }
      
      // Handle video call invitations with sound popup
      if (notification.type === 'video_call_invitation') {
        // Play notification sound
        playRingingSound();
        
        // Show video call invitation popup
        setVideoCallInvitation({
          sessionToken: notification.session_token,
          callerName: notification.caller,
          appointmentId: notification.appointment_id
        });
        setShowVideoCallInvitation(true);
        
        // Auto-hide popup after 30 seconds
        setTimeout(() => {
          setShowVideoCallInvitation(false);
          setVideoCallInvitation(null);
        }, 30000);
      }
      
      // Show browser notification for important updates
      if (Notification.permission === 'granted') {
        if (notification.type === 'appointment_accepted') {
          new Notification('Appointment Accepted', {
            body: `Doctor accepted your appointment for ${notification.patient_name}`,
            icon: '/favicon.ico'
          });
        } else if (notification.type === 'video_call_invitation') {
          new Notification('Video Call Invitation', {
            body: `${notification.caller} is inviting you to a video call`,
            icon: '/favicon.ico',
            requireInteraction: true
          });
        }
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    ws.onclose = () => {
      // Try to reconnect after 5 seconds
      setTimeout(setupWebSocket, 5000);
    };

    // Request notification permission
    if (Notification.permission === 'default') {
      Notification.requestPermission();
    }

    return () => ws.close();
  };

  const playRingingSound = () => {
    try {
      // Create a continuous ringing sound like a real phone
      const audioContext = new (window.AudioContext || window.webkitAudioContext)();
      
      let isRingingActive = true;
      const ringingInterval = setInterval(() => {
        if (!isRingingActive) {
          clearInterval(ringingInterval);
          return;
        }
        
        // Create ring tone (two quick tones)
        const createRingTone = (frequency, startTime, duration) => {
          const oscillator = audioContext.createOscillator();
          const gainNode = audioContext.createGain();
          
          oscillator.connect(gainNode);
          gainNode.connect(audioContext.destination);
          
          oscillator.type = 'sine';
          oscillator.frequency.value = frequency;
          
          gainNode.gain.setValueAtTime(0, startTime);
          gainNode.gain.linearRampToValueAtTime(0.15, startTime + 0.05);
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
      
      console.log('📞 Started phone ringing sound');
      return stopRinging;
      
    } catch (error) {
      console.error('Error creating ringing sound:', error);
      
      // Fallback to HTML5 Audio with looping
      try {
        const ringToneData = 'data:audio/wav;base64,UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAACBhYqFbF1fdJivrJBhNjVgodDbq2EcBj+a2/LDciUFLIHO8tiJNwgZaLvt559NEAxQp+PwtmMcBjiR1/LMeSwFJHfH8N2QQAoUXrTp6qNVFApGn+DyvGYfCSSLzfDVgjMGHW7A7+OZURE';
        const audio = new Audio(ringToneData);
        audio.loop = true;
        audio.volume = 0.4;
        
        audio.play().then(() => {
          console.log('📞 Fallback ringing sound playing');
          setRingingAudio(audio);
          setIsRinging(true);
        }).catch(fallbackError => {
          console.log('All ringing sounds failed');
        });
        
      } catch (fallbackError) {
        console.log('Unable to play ringing sound');
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
    if (videoCallInvitation) {
      navigate(`/video-call/${videoCallInvitation.sessionToken}`);
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
      // Get existing video call session for this appointment (or create if none exists)
      const response = await axios.get(`${API}/video-call/session/${appointmentId}`);
      const { session_token, status } = response.data;
      
      console.log(`${status === 'existing' ? 'Joining existing' : 'Creating new'} video call session: ${session_token}`);
      
      // Navigate to video call page
      navigate(`/video-call/${session_token}`);
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

      {/* Enhanced Video Call Invitation Popup - Like Real Phone Call */}
      {showVideoCallInvitation && videoCallInvitation && (
        <div className="fixed inset-0 bg-black bg-opacity-70 flex items-center justify-center z-50">
          <div className="glass-card max-w-md w-full mx-4">
            <div className="text-center p-8">
              {/* Phone Animation */}
              <div className="mb-6">
                <div className={`w-20 h-20 mx-auto rounded-full bg-green-500 flex items-center justify-center ${isRinging ? 'animate-pulse' : ''}`}>
                  <Phone className="w-10 h-10 text-white animate-bounce" />
                </div>
              </div>
              
              {/* Call Status */}
              <h3 className="text-2xl font-bold text-gray-900 mb-2">
                {isRinging ? 'Incoming Call...' : 'Video Call Invitation'}
              </h3>
              
              {/* Caller Info */}
              <div className="mb-2">
                <p className="text-xl font-semibold text-gray-800">
                  Dr. {videoCallInvitation.callerName}
                </p>
                <p className="text-sm text-gray-600">
                  {videoCallInvitation.appointmentType === 'emergency' ? '🚨 Emergency' : '📅 Regular'} Consultation
                </p>
              </div>
              
              {/* Ringing Indicator */}
              {isRinging && (
                <div className="mb-4">
                  <p className="text-sm text-gray-500 animate-pulse">
                    📞 Ringing...
                  </p>
                </div>
              )}
              
              {/* Call Action Buttons */}
              <div className="flex space-x-4 mt-6">
                <button
                  onClick={handleAcceptVideoCall}
                  className="flex-1 bg-green-500 hover:bg-green-600 text-white px-8 py-4 rounded-full font-semibold flex items-center justify-center space-x-2 transition-all transform hover:scale-105 shadow-lg"
                >
                  <Phone className="w-6 h-6" />
                  <span>Accept</span>
                </button>
                
                <button
                  onClick={handleDeclineVideoCall}
                  className="flex-1 bg-red-500 hover:bg-red-600 text-white px-8 py-4 rounded-full font-semibold flex items-center justify-center space-x-2 transition-all transform hover:scale-105 shadow-lg"
                >
                  <PhoneOff className="w-6 h-6" />
                  <span>Decline</span>
                </button>
              </div>
              
              {/* Auto-dismiss Timer */}
              <p className="text-xs text-gray-400 mt-4">
                Call will auto-dismiss in 30 seconds
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Dashboard;