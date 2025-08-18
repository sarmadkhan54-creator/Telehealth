import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Plus, Clock, AlertTriangle, User, LogOut, Calendar, Phone, X, Eye } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const Dashboard = ({ user, onLogout }) => {
  const [appointments, setAppointments] = useState([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    fetchAppointments();
  }, []);

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

                    {appointment.status === 'accepted' && (
                      <div className="ml-4">
                        <button
                          onClick={() => {
                            // Handle video call initiation
                            console.log('Starting video call for appointment:', appointment.id);
                          }}
                          className="btn-primary flex items-center space-x-2"
                        >
                          <Phone className="w-4 h-4" />
                          <span>Join Call</span>
                        </button>
                      </div>
                    )}
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

export default Dashboard;