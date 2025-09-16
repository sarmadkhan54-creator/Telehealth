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
  PhoneCall
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
      setNotifications(prev => [notification, ...prev.slice(0, 4)]);
      
      // Auto-refresh appointments when receiving notifications
      if (notification.type === 'emergency_appointment' || 
          notification.type === 'appointment_updated' ||
          notification.type === 'video_call_invitation') {
        fetchAppointments(); // Refresh appointments list
      }
      
      if (notification.type === 'emergency_appointment') {
        // Show browser notification for emergencies
        if (Notification.permission === 'granted') {
          new Notification('Emergency Appointment', {
            body: `${notification.patient_name} needs immediate consultation`,
            icon: '/favicon.ico'
          });
        }
      } else if (notification.type === 'video_call_invitation') {
        if (Notification.permission === 'granted') {
          new Notification('Video Call Invitation', {
            body: `${notification.caller} is inviting you to a video call`,
            icon: '/favicon.ico'
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

  const handleAcceptAppointment = async (appointmentId) => {
    try {
      await axios.put(`${API}/appointments/${appointmentId}`, {
        status: 'accepted',
        doctor_id: user.id
      });
      fetchAppointments();
    } catch (error) {
      console.error('Error accepting appointment:', error);
    }
  };

  const handleCompleteAppointment = async (appointmentId) => {
    try {
      await axios.put(`${API}/appointments/${appointmentId}`, {
        status: 'completed'
      });
      fetchAppointments();
    } catch (error) {
      console.error('Error completing appointment:', error);
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

  const sendNoteToProvider = async () => {
    if (!noteText.trim() || !selectedAppointment) return;

    try {
      await axios.post(`${API}/appointments/${selectedAppointment.id}/notes`, {
        note: noteText,
        sender_role: 'doctor',
        timestamp: new Date().toISOString()
      });

      alert('Note sent to provider successfully!');
      setNoteText('');
      
      // Refresh notes
      const notesResponse = await axios.get(`${API}/appointments/${selectedAppointment.id}/notes`);
      setAppointmentNotes(notesResponse.data);
    } catch (error) {
      console.error('Error sending note:', error);
      alert('Error sending note to provider');
    }
  };

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

  const pendingAppointments = appointments.filter(apt => apt.status === 'pending');
  const myAppointments = appointments.filter(apt => apt.doctor_id === user.id);

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
              <p className="text-sm text-gray-600">Doctor Dashboard</p>
            </div>
          </div>
          
          <div className="flex items-center space-x-4">
            {/* Notifications */}
            <button
              onClick={() => setShowNotificationPanel(true)}
              className="relative flex items-center space-x-2 px-3 py-2 text-green-600 hover:bg-green-50 rounded-lg transition-colors"
              title="Notifications"
            >
              <Bell className="w-6 h-6 text-gray-600" />
              {notifications.filter(n => !n.isRead).length > 0 && (
                <span className="absolute -top-1 -right-1 bg-red-500 text-white text-xs font-bold px-1 py-0.5 rounded-full min-w-[16px] h-4 flex items-center justify-center">
                  {notifications.filter(n => !n.isRead).length}
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
              Pending Requests
            </h3>
            <div className="text-center">
              <div className="text-3xl font-bold text-orange-600 mb-2">
                {pendingAppointments.length}
              </div>
              <p className="text-gray-600">Awaiting response</p>
            </div>
          </div>

          <div className="glass-card">
            <h3 className="text-xl font-semibold text-gray-900 mb-4 flex items-center">
              <CheckCircle className="w-6 h-6 mr-2 text-green-600" />
              My Appointments
            </h3>
            <div className="text-center">
              <div className="text-3xl font-bold text-green-600 mb-2">
                {myAppointments.length}
              </div>
              <p className="text-gray-600">Active cases</p>
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

        {/* Pending Appointments */}
        <div className="glass-card mb-8">
          <h2 className="text-2xl font-bold text-gray-900 mb-6 flex items-center">
            <Clock className="w-7 h-7 mr-3 text-orange-600" />
            Pending Appointments
          </h2>

          {pendingAppointments.length === 0 ? (
            <div className="text-center py-8">
              <Clock className="w-16 h-16 text-gray-300 mx-auto mb-4" />
              <p className="text-gray-500 text-lg">No pending appointments</p>
            </div>
          ) : (
            <div className="space-y-4">
              {pendingAppointments.map((appointment) => (
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
                        <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                          appointment.appointment_type === 'emergency' 
                            ? 'bg-red-100 text-red-800' 
                            : 'bg-green-100 text-green-800'
                        }`}>
                          {appointment.appointment_type === 'emergency' ? 'EMERGENCY' : 'ROUTINE'}
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
                          <p className="text-gray-600">Consultation Reason</p>
                          <p className="font-medium">
                            {appointment.patient?.consultation_reason}
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
                            </div>
                          </div>
                        )}
                      </div>
                    </div>

                    <div className="ml-4 flex flex-col space-y-2">
                      <button
                        onClick={() => handleAcceptAppointment(appointment.id)}
                        className="btn-primary flex items-center space-x-2"
                      >
                        <CheckCircle className="w-4 h-4" />
                        <span>Accept</span>
                      </button>
                      <button
                        onClick={() => viewAppointmentDetails(appointment)}
                        className="btn-secondary flex items-center space-x-2"
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

        {/* My Active Appointments */}
        <div className="glass-card">
          <h2 className="text-2xl font-bold text-gray-900 mb-6 flex items-center">
            <Phone className="w-7 h-7 mr-3 text-green-600" />
            My Active Appointments
          </h2>

          {myAppointments.length === 0 ? (
            <div className="text-center py-8">
              <Calendar className="w-16 h-16 text-gray-300 mx-auto mb-4" />
              <p className="text-gray-500 text-lg">No active appointments</p>
            </div>
          ) : (
            <div className="space-y-4">
              {myAppointments.map((appointment) => (
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
                          <p className="text-gray-600">Consultation Reason</p>
                          <p className="font-medium">
                            {appointment.patient?.consultation_reason}
                          </p>
                        </div>
                      </div>
                    </div>

                    <div className="ml-4 flex flex-col space-y-2">
                      {appointment.status === 'accepted' && (
                        <>
                          <CallButton
                            appointmentId={appointment.id}
                            targetUser={appointment.provider}
                            currentUser={user}
                            size="medium"
                            variant="primary"
                          />
                        </>
                      )}
                      
                      {appointment.status === 'pending' && (
                        <button
                          onClick={() => handleAcceptAppointment(appointment.id)}
                          className="btn-primary flex items-center space-x-2"
                        >
                          <CheckCircle className="w-4 h-4" />
                          <span>Accept</span>
                        </button>
                      )}
                      
                      {appointment.status === 'accepted' && (
                          <button
                            onClick={() => handleCompleteAppointment(appointment.id)}
                            className="btn-secondary flex items-center space-x-2"
                          >
                            <CheckCircle className="w-4 h-4" />
                            <span>Complete</span>
                          </button>
                        </>
                      )}
                      
                      {/* Enhanced options for ALL appointments */}
                      <button
                        onClick={() => viewAppointmentDetails(appointment)}
                        className="btn-secondary flex items-center space-x-2"
                      >
                        <Eye className="w-4 h-4" />
                        <span>View Details</span>
                      </button>
                      
                      {/* Doctors can call providers for any appointment */}
                      <CallButton
                        appointmentId={appointment.id}
                        targetUser={appointment.provider}
                        currentUser={user}
                        size="small"
                        variant="outline"
                      />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

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
                    onClick={sendNoteToProvider}
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
              {selectedAppointment.appointment_type === 'non_emergency' && (
                <button
                  onClick={() => callProvider(selectedAppointment)}
                  className="btn-secondary flex items-center space-x-2"
                >
                  <PhoneCall className="w-4 h-4" />
                  <span>Call Provider</span>
                </button>
              )}
              
              {selectedAppointment.status === 'pending' && (
                <button
                  onClick={() => handleAcceptAppointment(selectedAppointment.id)}
                  className="btn-primary flex items-center space-x-2"
                >
                  <CheckCircle className="w-4 h-4" />
                  <span>Accept Appointment</span>
                </button>
              )}
              
              {selectedAppointment.status === 'accepted' && (
                <>
                  <button
                    onClick={() => startVideoCall(selectedAppointment.id)}
                    className="btn-primary flex items-center space-x-2"
                  >
                    <Video className="w-4 h-4" />
                    <span>Start Video Call</span>
                  </button>
                  <button
                    onClick={() => handleCompleteAppointment(selectedAppointment.id)}
                    className="btn-secondary flex items-center space-x-2"
                  >
                    <CheckCircle className="w-4 h-4" />
                    <span>Mark Complete</span>
                  </button>
                </>
              )}
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