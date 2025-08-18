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
  Video
} from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const DoctorDashboard = ({ user, onLogout }) => {
  const [appointments, setAppointments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [notifications, setNotifications] = useState([]);
  const navigate = useNavigate();

  useEffect(() => {
    fetchAppointments();
    setupWebSocket();
  }, []);

  const setupWebSocket = () => {
    const wsUrl = `${BACKEND_URL.replace('https:', 'wss:').replace('http:', 'ws:')}/ws/${user.id}`;
    const ws = new WebSocket(wsUrl);
    
    ws.onmessage = (event) => {
      const notification = JSON.parse(event.data);
      setNotifications(prev => [notification, ...prev.slice(0, 4)]);
      
      if (notification.type === 'emergency_appointment') {
        // Show browser notification for emergencies
        if (Notification.permission === 'granted') {
          new Notification('Emergency Appointment', {
            body: `${notification.patient_name} needs immediate consultation`,
            icon: '/favicon.ico'
          });
        }
      }
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
      const response = await axios.post(`${API}/video-call/start/${appointmentId}`);
      const { session_token } = response.data;
      navigate(`/video-call/${session_token}`);
    } catch (error) {
      console.error('Error starting video call:', error);
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
            <div className="relative">
              <Bell className="w-6 h-6 text-gray-600" />
              {notifications.length > 0 && (
                <span className="absolute -top-1 -right-1 bg-red-500 text-white text-xs rounded-full h-5 w-5 flex items-center justify-center">
                  {notifications.length}
                </span>
              )}
            </div>
            
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
                          <button
                            onClick={() => startVideoCall(appointment.id)}
                            className="btn-primary flex items-center space-x-2"
                          >
                            <Video className="w-4 h-4" />
                            <span>Start Call</span>
                          </button>
                          <button
                            onClick={() => handleCompleteAppointment(appointment.id)}
                            className="btn-secondary flex items-center space-x-2"
                          >
                            <CheckCircle className="w-4 h-4" />
                            <span>Complete</span>
                          </button>
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
    </div>
  );
};

export default DoctorDashboard;