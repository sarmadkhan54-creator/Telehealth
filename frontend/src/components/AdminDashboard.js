import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { 
  Users, 
  UserPlus, 
  BarChart3, 
  Calendar, 
  LogOut, 
  Shield,
  Activity,
  Phone,
  Clock,
  CheckCircle,
  AlertTriangle,
  Settings,
  Download,
  Eye,
  EyeOff,
  Edit,
  Trash2
} from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Set up axios defaults for authentication
const getAxiosConfig = () => {
  const token = localStorage.getItem('authToken');
  return {
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    }
  };
};

const AdminDashboard = ({ user, onLogout }) => {
  const [activeTab, setActiveTab] = useState('overview');
  const [users, setUsers] = useState([]);
  const [appointments, setAppointments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showAddUserForm, setShowAddUserForm] = useState(false);
  const [showEditAppointmentModal, setShowEditAppointmentModal] = useState(false);
  const [showEditUserModal, setShowEditUserModal] = useState(false);
  const [editingAppointment, setEditingAppointment] = useState(null);
  const [editingUser, setEditingUser] = useState(null);

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
    if (user.role !== 'admin') {
      alert('Access Denied: Only administrators can access this dashboard');
      onLogout();
      return;
    }
    fetchData();
    setupWebSocket();
    
    return () => {
      // Cleanup will be handled by separate polling useEffect
    };
  }, [user.role, onLogout]);

  useEffect(() => {
    // AGGRESSIVE Auto-refresh data every 5 seconds for real-time sync
    console.log('🔄 Setting up aggressive 5-second polling for Admin Dashboard');
    const refreshInterval = setInterval(() => {
      console.log('⏰ Admin auto-refresh triggered (5s interval)');
      fetchData();
    }, 5000); // Refresh every 5 seconds for real-time feel
    
    return () => {
      clearInterval(refreshInterval);
    };
  }, []);

  const setupWebSocket = () => {
    const wsUrl = `${BACKEND_URL.replace('https:', 'wss:').replace('http:', 'ws:')}/api/ws/${user.id}`;
    const ws = new WebSocket(wsUrl);
    
    ws.onmessage = (event) => {
      const notification = JSON.parse(event.data);
      
      // Auto-refresh data when receiving notifications
      if (notification.type === 'emergency_appointment' || 
          notification.type === 'appointment_accepted' || 
          notification.type === 'appointment_updated' ||
          notification.type === 'appointment_deleted' ||
          notification.type === 'user_created' ||
          notification.type === 'user_updated' ||
          notification.type === 'user_deleted' ||
          notification.type === 'user_permanently_deleted' ||
          notification.type === 'new_appointment_created') {
        console.log('📡 Admin Dashboard: Received real-time update, refreshing data...', notification.type);
        fetchData(); // Refresh all data for instant UI update
      }
      
      // Show browser notification for admin updates
      if (Notification.permission === 'granted') {
        if (notification.type === 'emergency_appointment') {
          showNotification('Emergency Appointment', {
            body: `Emergency appointment created by ${notification.provider_name}`,
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

  const fetchData = async () => {
    try {
      const [usersResponse, appointmentsResponse] = await Promise.all([
        axios.get(`${API}/users`, getAxiosConfig()),
        axios.get(`${API}/appointments`, getAxiosConfig())
      ]);
      
      setUsers(usersResponse.data);
      setAppointments(appointmentsResponse.data);
    } catch (error) {
      console.error('Error fetching data:', error);
    } finally {
      setLoading(false);
    }
  };

  const getStats = () => {
    const providers = users.filter(u => u.role === 'provider');
    const doctors = users.filter(u => u.role === 'doctor');
    const emergencyAppts = appointments.filter(a => a.appointment_type === 'emergency');
    const completedAppts = appointments.filter(a => a.status === 'completed');
    const todayAppts = appointments.filter(a => {
      const today = new Date().toDateString();
      const apptDate = new Date(a.created_at).toDateString();
      return today === apptDate;
    });

    return {
      totalUsers: users.length,
      providers: providers.length,
      doctors: doctors.length,
      totalAppointments: appointments.length,
      emergencyAppointments: emergencyAppts.length,
      completedAppointments: completedAppts.length,
      todayAppointments: todayAppts.length
    };
  };

  const stats = getStats();

  const AddUserForm = () => {
    const [formData, setFormData] = useState({
      username: '',
      email: '',
      password: '',
      phone: '',
      full_name: '',
      role: '',
      district: '',
      specialty: ''
    });
    const [showPassword, setShowPassword] = useState(false);

    const handleSubmit = async (e) => {
      e.preventDefault();
      try {
        await axios.post(`${API}/admin/create-user`, formData, getAxiosConfig());
        setShowAddUserForm(false);
        fetchData();
        alert('User added successfully!');
        setFormData({
          username: '',
          email: '',
          password: '',
          phone: '',
          full_name: '',
          role: '',
          district: '',
          specialty: ''
        });
      } catch (error) {
        alert(error.response?.data?.detail || 'Error adding user');
      }
    };

    const handleChange = (e) => {
      setFormData({
        ...formData,
        [e.target.name]: e.target.value
      });
    };

    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="glass-card max-w-2xl w-full max-h-[90vh] overflow-y-auto">
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-2xl font-bold text-gray-900">Add New User</h3>
            <button
              onClick={() => setShowAddUserForm(false)}
              className="text-gray-500 hover:text-gray-700"
            >
              ×
            </button>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="form-group">
                <label className="form-label">Username *</label>
                <input
                  type="text"
                  name="username"
                  required
                  className="form-input"
                  value={formData.username}
                  onChange={handleChange}
                />
              </div>

              <div className="form-group">
                <label className="form-label">Email *</label>
                <input
                  type="email"
                  name="email"
                  required
                  className="form-input"
                  value={formData.email}
                  onChange={handleChange}
                />
              </div>

              <div className="form-group">
                <label className="form-label">Password *</label>
                <div className="relative">
                  <input
                    type={showPassword ? 'text' : 'password'}
                    name="password"
                    required
                    className="form-input pr-10"
                    value={formData.password}
                    onChange={handleChange}
                  />
                  <button
                    type="button"
                    className="absolute right-3 top-1/2 transform -translate-y-1/2"
                    onClick={() => setShowPassword(!showPassword)}
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              <div className="form-group">
                <label className="form-label">Phone *</label>
                <input
                  type="tel"
                  name="phone"
                  required
                  className="form-input"
                  value={formData.phone}
                  onChange={handleChange}
                />
              </div>

              <div className="form-group md:col-span-2">
                <label className="form-label">Full Name *</label>
                <input
                  type="text"
                  name="full_name"
                  required
                  className="form-input"
                  value={formData.full_name}
                  onChange={handleChange}
                />
              </div>

              <div className="form-group">
                <label className="form-label">Role *</label>
                <select
                  name="role"
                  required
                  className="form-input"
                  value={formData.role}
                  onChange={handleChange}
                >
                  <option value="">Select role</option>
                  <option value="admin">Admin</option>
                  <option value="provider">Provider</option>
                  <option value="doctor">Doctor</option>
                </select>
              </div>

              <div className="form-group">
                <label className="form-label">District</label>
                <input
                  type="text"
                  name="district"
                  className="form-input"
                  value={formData.district}
                  onChange={handleChange}
                />
              </div>

              {formData.role === 'doctor' && (
                <div className="form-group md:col-span-2">
                  <label className="form-label">Specialty</label>
                  <input
                    type="text"
                    name="specialty"
                    className="form-input"
                    placeholder="e.g., Cardiology, General Medicine"
                    value={formData.specialty}
                    onChange={handleChange}
                  />
                </div>
              )}
            </div>

            <div className="flex justify-end space-x-4 pt-6">
              <button
                type="button"
                onClick={() => setShowAddUserForm(false)}
                className="btn-secondary"
              >
                Cancel
              </button>
              <button type="submit" className="btn-primary">
                Add User
              </button>
            </div>
          </form>
        </div>
      </div>
    );
  };

  const EditAppointmentModal = () => {
    const [formData, setFormData] = useState({
      status: editingAppointment?.status || '',
      appointment_type: editingAppointment?.appointment_type || '',
      patient: {
        name: editingAppointment?.patient?.name || '',
        age: editingAppointment?.patient?.age || '',
        gender: editingAppointment?.patient?.gender || '',
        consultation_reason: editingAppointment?.patient?.consultation_reason || '',
        vitals: {
          blood_pressure: editingAppointment?.patient?.vitals?.blood_pressure || '',
          heart_rate: editingAppointment?.patient?.vitals?.heart_rate || '',
          temperature: editingAppointment?.patient?.vitals?.temperature || '',
          oxygen_saturation: editingAppointment?.patient?.vitals?.oxygen_saturation || ''
        }
      }
    });

    useEffect(() => {
      if (editingAppointment) {
        setFormData({
          status: editingAppointment.status,
          appointment_type: editingAppointment.appointment_type,
          patient: {
            name: editingAppointment.patient?.name || '',
            age: editingAppointment.patient?.age || '',
            gender: editingAppointment.patient?.gender || '',
            consultation_reason: editingAppointment.patient?.consultation_reason || '',
            vitals: {
              blood_pressure: editingAppointment.patient?.vitals?.blood_pressure || '',
              heart_rate: editingAppointment.patient?.vitals?.heart_rate || '',
              temperature: editingAppointment.patient?.vitals?.temperature || '',
              oxygen_saturation: editingAppointment.patient?.vitals?.oxygen_saturation || ''
            }
          }
        });
      }
    }, [editingAppointment]);

    const handleSubmit = async (e) => {
      e.preventDefault();
      try {
        await axios.put(`${API}/appointments/${editingAppointment.id}`, formData, getAxiosConfig());
        setShowEditAppointmentModal(false);
        setEditingAppointment(null);
        fetchData();
        alert('Appointment updated successfully!');
      } catch (error) {
        console.error('Error updating appointment:', error);
        alert(error.response?.data?.detail || 'Error updating appointment');
      }
    };

    const handleChange = (e) => {
      const { name, value } = e.target;
      if (name.startsWith('patient.')) {
        const field = name.split('.')[1];
        if (field.startsWith('vitals.')) {
          const vital = field.split('.')[1];
          setFormData(prev => ({
            ...prev,
            patient: {
              ...prev.patient,
              vitals: {
                ...prev.patient.vitals,
                [vital]: value
              }
            }
          }));
        } else {
          setFormData(prev => ({
            ...prev,
            patient: {
              ...prev.patient,
              [field]: value
            }
          }));
        }
      } else {
        setFormData(prev => ({
          ...prev,
          [name]: value
        }));
      }
    };

    if (!editingAppointment) return null;

    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="glass-card max-w-4xl w-full max-h-[90vh] overflow-y-auto">
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-2xl font-bold text-gray-900">Edit Appointment</h3>
            <button
              onClick={() => {
                setShowEditAppointmentModal(false);
                setEditingAppointment(null);
              }}
              className="text-gray-500 hover:text-gray-700"
            >
              ×
            </button>
          </div>

          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Appointment Status & Type */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="form-group">
                <label className="form-label">Status *</label>
                <select
                  name="status"
                  required
                  className="form-input"
                  value={formData.status}
                  onChange={handleChange}
                >
                  <option value="pending">Pending</option>
                  <option value="accepted">Accepted</option>
                  <option value="completed">Completed</option>
                  <option value="cancelled">Cancelled</option>
                </select>
              </div>

              <div className="form-group">
                <label className="form-label">Type *</label>
                <select
                  name="appointment_type"
                  required
                  className="form-input"
                  value={formData.appointment_type}
                  onChange={handleChange}
                >
                  <option value="emergency">Emergency</option>
                  <option value="non_emergency">Non-Emergency</option>
                </select>
              </div>
            </div>

            {/* Patient Information */}
            <div className="glass-card">
              <h4 className="text-lg font-semibold text-gray-900 mb-4">Patient Information</h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="form-group">
                  <label className="form-label">Patient Name *</label>
                  <input
                    type="text"
                    name="patient.name"
                    required
                    className="form-input"
                    value={formData.patient.name}
                    onChange={handleChange}
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">Age *</label>
                  <input
                    type="number"
                    name="patient.age"
                    required
                    min="1"
                    max="150"
                    className="form-input"
                    value={formData.patient.age}
                    onChange={handleChange}
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">Gender *</label>
                  <select
                    name="patient.gender"
                    required
                    className="form-input"
                    value={formData.patient.gender}
                    onChange={handleChange}
                  >
                    <option value="">Select gender</option>
                    <option value="male">Male</option>
                    <option value="female">Female</option>
                    <option value="other">Other</option>
                  </select>
                </div>

                <div className="form-group md:col-span-1">
                  <label className="form-label">Consultation Reason *</label>
                  <textarea
                    name="patient.consultation_reason"
                    required
                    rows={3}
                    className="form-input"
                    value={formData.patient.consultation_reason}
                    onChange={handleChange}
                  />
                </div>
              </div>
            </div>

            {/* Patient Vitals */}
            <div className="glass-card">
              <h4 className="text-lg font-semibold text-gray-900 mb-4">Patient Vitals (Optional)</h4>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="form-group">
                  <label className="form-label">Blood Pressure</label>
                  <input
                    type="text"
                    name="patient.vitals.blood_pressure"
                    className="form-input"
                    placeholder="e.g., 120/80"
                    value={formData.patient.vitals.blood_pressure}
                    onChange={handleChange}
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">Heart Rate</label>
                  <input
                    type="number"
                    name="patient.vitals.heart_rate"
                    className="form-input"
                    placeholder="BPM"
                    value={formData.patient.vitals.heart_rate}
                    onChange={handleChange}
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">Temperature</label>
                  <input
                    type="number"
                    name="patient.vitals.temperature"
                    className="form-input"
                    step="0.1"
                    placeholder="°C"
                    value={formData.patient.vitals.temperature}
                    onChange={handleChange}
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">Oxygen Saturation</label>
                  <input
                    type="number"
                    name="patient.vitals.oxygen_saturation"
                    className="form-input"
                    min="0"
                    max="100"
                    placeholder="%"
                    value={formData.patient.vitals.oxygen_saturation}
                    onChange={handleChange}
                  />
                </div>
              </div>
            </div>

            <div className="flex justify-end space-x-4 pt-6">
              <button
                type="button"
                onClick={() => {
                  setShowEditAppointmentModal(false);
                  setEditingAppointment(null);
                }}
                className="btn-secondary"
              >
                Cancel
              </button>
              <button type="submit" className="btn-primary">
                Update Appointment
              </button>
            </div>
          </form>
        </div>
      </div>
    );
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleString();
  };

  // Export functionality
  const exportToCSV = (data, filename) => {
    if (!data || data.length === 0) {
      alert('No data to export');
      return;
    }

    const csvContent = convertToCSV(data);
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    
    if (link.download !== undefined) {
      const url = URL.createObjectURL(blob);
      link.setAttribute('href', url);
      link.setAttribute('download', filename);
      link.style.visibility = 'hidden';
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    }
  };

  const convertToCSV = (data) => {
    if (!data || data.length === 0) return '';
    
    const headers = Object.keys(data[0]);
    const csvHeaders = headers.join(',');
    
    const csvRows = data.map(row => {
      return headers.map(header => {
        let value = row[header];
        if (value === null || value === undefined) {
          value = '';
        } else if (typeof value === 'object') {
          value = JSON.stringify(value);
        } else {
          value = String(value);
        }
        // Escape quotes and wrap in quotes if contains comma or quote
        if (value.includes(',') || value.includes('"') || value.includes('\n')) {
          value = '"' + value.replace(/"/g, '""') + '"';
        }
        return value;
      }).join(',');
    });
    
    return [csvHeaders, ...csvRows].join('\n');
  };

  const exportAppointments = () => {
    const exportData = appointments.map(appointment => ({
      'Patient Name': appointment.patient?.name || '',
      'Age': appointment.patient?.age || '',
      'Gender': appointment.patient?.gender || '',
      'Consultation Reason': appointment.patient?.consultation_reason || '',
      'Provider': appointment.provider?.full_name || '',
      'Provider District': appointment.provider?.district || '',
      'Doctor': appointment.doctor?.full_name || 'Unassigned',
      'Doctor Specialty': appointment.doctor?.specialty || '',
      'Type': appointment.appointment_type,
      'Status': appointment.status,
      'Created Date': formatDate(appointment.created_at),
      'Blood Pressure': appointment.patient?.vitals?.blood_pressure || '',
      'Heart Rate': appointment.patient?.vitals?.heart_rate || '',
      'Temperature': appointment.patient?.vitals?.temperature || '',
      'Oxygen Saturation': appointment.patient?.vitals?.oxygen_saturation || '',
    }));
    
    const filename = `greenstar-appointments-${new Date().toISOString().split('T')[0]}.csv`;
    exportToCSV(exportData, filename);
  };

  const exportUsers = () => {
    const exportData = users.map(user => ({
      'Full Name': user.full_name,
      'Username': user.username,
      'Email': user.email,
      'Phone': user.phone,
      'Role': user.role,
      'District': user.district || '',
      'Specialty': user.specialty || '',
      'Status': user.is_active ? 'Active' : 'Inactive',
      'Created Date': formatDate(user.created_at)
    }));
    
    const filename = `greenstar-users-${new Date().toISOString().split('T')[0]}.csv`;
    exportToCSV(exportData, filename);
  };

  const exportMonthlyReport = () => {
    const currentMonth = new Date().toLocaleString('default', { month: 'long', year: 'numeric' });
    const monthlyData = [
      {
        'Report Type': 'Monthly Summary',
        'Month': currentMonth,
        'Total Users': stats.totalUsers,
        'Total Providers': stats.providers,
        'Total Doctors': stats.doctors,
        'Total Appointments': stats.totalAppointments,
        'Emergency Appointments': stats.emergencyAppointments,
        'Completed Appointments': stats.completedAppointments,
        'Today Appointments': stats.todayAppointments,
        'Generated Date': new Date().toLocaleString()
      }
    ];
    
    // Add provider performance data
    const providerStats = users.filter(u => u.role === 'provider').map(provider => {
      const providerAppts = appointments.filter(a => a.provider_id === provider.id);
      return {
        'Report Type': 'Provider Performance',
        'Provider Name': provider.full_name,
        'District': provider.district || '',
        'Total Appointments': providerAppts.length,
        'Emergency Calls': providerAppts.filter(a => a.appointment_type === 'emergency').length,
        'Completed Calls': providerAppts.filter(a => a.status === 'completed').length,
        'Generated Date': new Date().toLocaleString()
      };
    });
    
    const combinedData = [...monthlyData, ...providerStats];
    const filename = `greenstar-monthly-report-${new Date().toISOString().split('T')[0]}.csv`;
    exportToCSV(combinedData, filename);
  };

  const handleCleanupAllAppointments = async () => {
    if (user.role !== 'admin') {
      alert('Access Denied: Only administrators can perform cleanup operations');
      return;
    }

    const confirmed = window.confirm(`⚠️ WARNING: This will permanently delete ALL appointments, patient data, and notes. Are you absolutely sure you want to proceed?`);
    if (!confirmed) return;

    const doubleConfirmed = window.confirm(`🚨 FINAL CONFIRMATION: This action cannot be undone and will remove all historical data. Type 'DELETE ALL' to proceed.`);
    if (!doubleConfirmed) return;

    try {
      console.log('Attempting to cleanup all appointments...');
      
      const response = await axios.delete(`${API}/admin/appointments/cleanup`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('authToken')}`,
          'Content-Type': 'application/json'
        }
      });
      
      console.log('Cleanup response:', response.data);
      
      // Clear appointments state immediately
      setAppointments([]);
      
      alert(`Cleanup completed successfully! Deleted: ${response.data.deleted.appointments} appointments, ${response.data.deleted.notes} notes, ${response.data.deleted.patients} patients`);
      
      // Refresh data to confirm cleanup
      await fetchData();
      
    } catch (error) {
      console.error('Error during cleanup:', error);
      alert(error.response?.data?.detail || 'Failed to cleanup appointments. Please try again.');
      await fetchData();
    }
  };

  // User management functions (Admin only)
  const handleViewPassword = async (userId, username) => {
    if (user.role !== 'admin') {
      alert('Access Denied: Only administrators can view passwords');
      return;
    }

    try {
      const response = await axios.get(`${API}/admin/users/${userId}/password`, getAxiosConfig());
      alert(`Password for ${username}: ${response.data.password}`);
    } catch (error) {
      console.error('Error fetching password:', error);
      alert(error.response?.data?.detail || 'Failed to fetch password');
    }
  };

  const handlePermanentDeleteUser = async (userId, userName) => {
    if (user.role !== 'admin') {
      alert('Access Denied: Only administrators can permanently delete users');
      return;
    }

    if (userId === user.id) {
      alert('Error: You cannot delete your own admin account');
      return;
    }

    const confirmed = window.confirm(`⚠️ PERMANENT DELETE: Are you sure you want to permanently delete user "${userName}"? This action cannot be undone and will remove all associated data.`);
    if (!confirmed) return;

    const doubleConfirmed = window.confirm(`🚨 FINAL CONFIRMATION: This will permanently remove "${userName}" and all their data from the system. Type 'PERMANENT DELETE' to proceed.`);
    if (!doubleConfirmed) return;

    try {
      console.log('Attempting to permanently delete user:', userId);
      
      const response = await axios.delete(`${API}/admin/users/${userId}/permanent`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('authToken')}`,
          'Content-Type': 'application/json'
        }
      });
      
      console.log('Permanent delete response:', response.data);
      
      // Force immediate UI update by filtering out the deleted user
      setUsers(prevUsers => {
        const updatedUsers = prevUsers.filter(u => u.id !== userId);
        console.log('🗑️ User removed from UI immediately:', updatedUsers.length, 'users remaining');
        return updatedUsers;
      });
      
      alert(`User "${userName}" permanently deleted successfully`);
      
      // Force multiple refresh attempts to ensure UI updates
      setTimeout(async () => {
        console.log('First refresh after permanent user deletion...');
        await fetchData();
      }, 100);
      
      setTimeout(async () => {
        console.log('Second refresh after permanent user deletion...');
        await fetchData();
      }, 1000);
      
    } catch (error) {
      console.error('Error permanently deleting user:', error);
      alert(error.response?.data?.detail || 'Failed to permanently delete user');
      // Refresh data even on error to check current state
      await fetchData();
    }
  };

  const handleEditUser = (userId) => {
    if (user.role !== 'admin') {
      alert('Access Denied: Only administrators can edit users');
      return;
    }
    
    const userToEdit = users.find(u => u.id === userId);
    if (userToEdit) {
      setEditingUser({
        id: userToEdit.id,
        full_name: userToEdit.full_name,
        email: userToEdit.email,
        phone: userToEdit.phone,
        district: userToEdit.district,
        specialty: userToEdit.specialty || '',
        is_active: userToEdit.is_active
      });
      setShowEditUserModal(true);
    }
  };

  const handleUpdateUser = async (e) => {
    e.preventDefault();
    
    try {
      await axios.put(`${API}/users/${editingUser.id}`, {
        full_name: editingUser.full_name,
        email: editingUser.email,
        phone: editingUser.phone,
        district: editingUser.district,
        specialty: editingUser.specialty,
        is_active: editingUser.is_active
      }, getAxiosConfig());
      
      alert('User updated successfully');
      setShowEditUserModal(false);
      setEditingUser(null);
      fetchData(); // Refresh the users list
    } catch (error) {
      console.error('Error updating user:', error);
      alert(error.response?.data?.detail || 'Failed to update user');
    }
  };

  const handleDeleteUser = async (userId, userName) => {
    if (user.role !== 'admin') {
      alert('Access Denied: Only administrators can delete users');
      return;
    }

    if (userId === user.id) {
      alert('Error: You cannot delete your own admin account');
      return;
    }

    const confirmed = window.confirm(`Are you sure you want to delete user "${userName}"? This action cannot be undone.`);
    if (!confirmed) return;

    try {
      console.log('Attempting to delete user:', userId);
      
      const response = await axios.delete(`${API}/users/${userId}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('authToken')}`,
          'Content-Type': 'application/json'
        }
      });
      
      console.log('Delete response:', response.data);
      
      // Force immediate UI update by filtering out the deleted user
      setUsers(prevUsers => {
        const updatedUsers = prevUsers.filter(u => u.id !== userId);
        console.log('🗑️ User removed from UI immediately:', updatedUsers.length, 'users remaining');
        return updatedUsers;
      });
      
      alert(`User "${userName}" deleted successfully`);
      
      // Force multiple refresh attempts to ensure UI updates
      setTimeout(async () => {
        console.log('First refresh after user deletion...');
        await fetchData();
      }, 100);
      
      setTimeout(async () => {
        console.log('Second refresh after user deletion...');
        await fetchData();
      }, 1000);
      
    } catch (error) {
      console.error('Error deleting user:', error);
      alert(error.response?.data?.detail || 'Failed to delete user');
      // Refresh data even on error to check current state
      await fetchData();
    }
  };

  const handleToggleUserStatus = async (userId, currentStatus, userName) => {
    if (user.role !== 'admin') {
      alert('Access Denied: Only administrators can modify user status');
      return;
    }

    if (userId === user.id) {
      alert('Error: You cannot deactivate your own admin account');
      return;
    }

    const action = currentStatus ? 'deactivate' : 'activate';
    const confirmed = window.confirm(`Are you sure you want to ${action} user "${userName}"?`);
    if (!confirmed) return;

    try {
      await axios.put(
        `${API}/users/${userId}/status`, 
        { is_active: !currentStatus },
        getAxiosConfig()
      );
      alert(`User ${action}d successfully`);
      fetchData(); // Refresh the users list
    } catch (error) {
      console.error('Error updating user status:', error);
      alert(error.response?.data?.detail || 'Failed to update user status');
    }
  };

  // Appointment management functions (Admin only)
  const EditUserModal = () => {
    if (!editingUser) return null;

    const handleChange = (e) => {
      const { name, value, type, checked } = e.target;
      setEditingUser(prev => ({
        ...prev,
        [name]: type === 'checkbox' ? checked : value
      }));
    };

    return (
      <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
        <div className="glass-card max-w-2xl w-full max-h-[90vh] overflow-y-auto mx-4">
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-2xl font-bold text-gray-900">Edit User</h3>
            <button
              onClick={() => {
                setShowEditUserModal(false);
                setEditingUser(null);
              }}
              className="text-gray-500 hover:text-gray-700 text-2xl"
            >
              ×
            </button>
          </div>

          <form onSubmit={handleUpdateUser} className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="form-group">
                <label className="form-label">Full Name *</label>
                <input
                  type="text"
                  name="full_name"
                  value={editingUser.full_name}
                  onChange={handleChange}
                  className="form-input"
                  required
                />
              </div>

              <div className="form-group">
                <label className="form-label">Email *</label>
                <input
                  type="email"
                  name="email"
                  value={editingUser.email}
                  onChange={handleChange}
                  className="form-input"
                  required
                />
              </div>

              <div className="form-group">
                <label className="form-label">Phone</label>
                <input
                  type="text"
                  name="phone"
                  value={editingUser.phone}
                  onChange={handleChange}
                  className="form-input"
                />
              </div>

              <div className="form-group">
                <label className="form-label">District</label>
                <input
                  type="text"
                  name="district"
                  value={editingUser.district}
                  onChange={handleChange}
                  className="form-input"
                />
              </div>

              <div className="form-group">
                <label className="form-label">Specialty</label>
                <input
                  type="text"
                  name="specialty"
                  value={editingUser.specialty}
                  onChange={handleChange}
                  className="form-input"
                  placeholder="e.g., Cardiology, General Practice"
                />
              </div>

              <div className="form-group">
                <label className="flex items-center space-x-2">
                  <input
                    type="checkbox"
                    name="is_active"
                    checked={editingUser.is_active}
                    onChange={handleChange}
                    className="form-checkbox"
                  />
                  <span className="form-label">Active User</span>
                </label>
              </div>
            </div>

            <div className="flex justify-end space-x-4 pt-6">
              <button
                type="button"
                onClick={() => {
                  setShowEditUserModal(false);
                  setEditingUser(null);
                }}
                className="btn-secondary"
              >
                Cancel
              </button>
              <button
                type="submit"
                className="btn-primary"
              >
                Update User
              </button>
            </div>
          </form>
        </div>
      </div>
    );
  };

  const handleEditAppointment = async (appointmentId) => {
    if (user.role !== 'admin') {
      alert('Access Denied: Only administrators can edit appointments');
      return;
    }
    
    try {
      // Fetch the appointment details
      const response = await axios.get(`${API}/appointments/${appointmentId}`, getAxiosConfig());
      setEditingAppointment(response.data);
      setShowEditAppointmentModal(true);
    } catch (error) {
      console.error('Error fetching appointment details:', error);
      alert('Error loading appointment details');
    }
  };

  const handleDeleteAppointment = async (appointmentId, patientName) => {
    if (user.role !== 'admin') {
      alert('Access Denied: Only administrators can delete appointments');
      return;
    }

    const confirmed = window.confirm(`Are you sure you want to delete the appointment for "${patientName}"? This action cannot be undone.`);
    if (!confirmed) return;

    try {
      console.log('Attempting to delete appointment:', appointmentId);
      
      const response = await axios.delete(`${API}/appointments/${appointmentId}`, {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('authToken')}`,
          'Content-Type': 'application/json'
        }
      });
      
      console.log('Delete appointment response:', response.data);
      
      // Force immediate UI update by filtering out the deleted appointment
      setAppointments(prevAppointments => {
        const updatedAppointments = prevAppointments.filter(a => a.id !== appointmentId);
        console.log('Updated appointments list:', updatedAppointments.length, 'appointments remaining');
        return updatedAppointments;
      });
      
      alert(`Appointment for "${patientName}" deleted successfully`);
      
      // Force multiple refresh attempts to ensure UI updates
      setTimeout(async () => {
        console.log('First refresh after appointment deletion...');
        await fetchData();
      }, 100);
      
      setTimeout(async () => {
        console.log('Second refresh after appointment deletion...');
        await fetchData();
      }, 1000);
      
    } catch (error) {
      console.error('Error deleting appointment:', error);
      console.error('Error details:', error.response?.data);
      alert(error.response?.data?.detail || 'Failed to delete appointment. Please try again.');
      // Refresh data even on error to check current state
      await fetchData();
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-green-50 to-emerald-100">
        <div className="loading-spinner"></div>
      </div>
    );
  }

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
              <h1 className="nav-brand text-green-700">Greenstar Digital Health Solutions - Admin</h1>
              <p className="text-sm text-gray-600">Administrative Dashboard</p>
            </div>
          </div>
          
          <div className="flex items-center space-x-4">
            <div className="text-right">
              <p className="font-semibold text-gray-900">{user.full_name}</p>
              <p className="text-sm text-gray-600">Administrator</p>
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
        {/* Tab Navigation */}
        <div className="glass-card mb-8">
          <div className="flex flex-wrap gap-2">
            {[
              { id: 'overview', label: 'Overview', icon: BarChart3 },
              { id: 'users', label: 'Users', icon: Users },
              { id: 'appointments', label: 'Appointments', icon: Calendar },
              { id: 'reports', label: 'Reports', icon: Activity }
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center space-x-2 px-4 py-2 rounded-lg transition-colors ${
                  activeTab === tab.id
                    ? 'bg-green-100 text-green-700 font-medium'
                    : 'text-gray-600 hover:bg-gray-50'
                }`}
              >
                <tab.icon className="w-4 h-4" />
                <span>{tab.label}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Overview Tab */}
        {activeTab === 'overview' && (
          <div className="space-y-8">
            {/* Stats Grid */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              <div className="glass-card">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-600">Total Users</p>
                    <p className="text-2xl font-bold text-gray-900">{stats.totalUsers}</p>
                  </div>
                  <Users className="w-8 h-8 text-green-500" />
                </div>
              </div>

              <div className="glass-card">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-600">Total Appointments</p>
                    <p className="text-2xl font-bold text-gray-900">{stats.totalAppointments}</p>
                  </div>
                  <Calendar className="w-8 h-8 text-green-500" />
                </div>
              </div>

              <div className="glass-card">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-600">Emergency Calls</p>
                    <p className="text-2xl font-bold text-red-600">{stats.emergencyAppointments}</p>
                  </div>
                  <AlertTriangle className="w-8 h-8 text-red-500" />
                </div>
              </div>

              <div className="glass-card">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-600">Completed Today</p>
                    <p className="text-2xl font-bold text-green-600">{stats.completedAppointments}</p>
                  </div>
                  <CheckCircle className="w-8 h-8 text-green-500" />
                </div>
              </div>
            </div>

            {/* User Distribution */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div className="glass-card">
                <h3 className="text-xl font-semibold text-gray-900 mb-4">User Distribution</h3>
                <div className="space-y-3">
                  <div className="flex justify-between items-center">
                    <span className="text-gray-600">Providers</span>
                    <span className="font-semibold">{stats.providers}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-gray-600">Doctors</span>
                    <span className="font-semibold">{stats.doctors}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-gray-600">Admins</span>
                    <span className="font-semibold">
                      {users.filter(u => u.role === 'admin').length}
                    </span>
                  </div>
                </div>
              </div>

              <div className="glass-card">
                <h3 className="text-xl font-semibold text-gray-900 mb-4">Today's Activity</h3>
                <div className="space-y-3">
                  <div className="flex justify-between items-center">
                    <span className="text-gray-600">New Appointments</span>
                    <span className="font-semibold">{stats.todayAppointments}</span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-gray-600">Emergency Calls</span>
                    <span className="font-semibold text-red-600">
                      {appointments.filter(a => {
                        const today = new Date().toDateString();
                        const apptDate = new Date(a.created_at).toDateString();
                        return today === apptDate && a.appointment_type === 'emergency';
                      }).length}
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-gray-600">Completed</span>
                    <span className="font-semibold text-green-600">
                      {appointments.filter(a => {
                        const today = new Date().toDateString();
                        const apptDate = new Date(a.created_at).toDateString();
                        return today === apptDate && a.status === 'completed';
                      }).length}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Users Tab */}
        {activeTab === 'users' && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <h2 className="text-2xl font-bold text-gray-900">User Management</h2>
              {/* Only show Add User button for admin users */}
              {user.role === 'admin' && (
                <button
                  onClick={() => setShowAddUserForm(true)}
                  className="btn-primary flex items-center space-x-2"
                >
                  <UserPlus className="w-4 h-4" />
                  <span>Add User</span>
                </button>
              )}
            </div>

            <div className="glass-card">
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="border-b border-gray-200">
                    <tr>
                      <th className="text-left py-3 px-4 font-semibold text-gray-900">Name</th>
                      <th className="text-left py-3 px-4 font-semibold text-gray-900">Role</th>
                      <th className="text-left py-3 px-4 font-semibold text-gray-900">District</th>
                      <th className="text-left py-3 px-4 font-semibold text-gray-900">Contact</th>
                      <th className="text-left py-3 px-4 font-semibold text-gray-900">Status</th>
                      <th className="text-left py-3 px-4 font-semibold text-gray-900">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {users.map((userItem) => (
                      <tr key={userItem.id} className="border-b border-gray-100">
                        <td className="py-3 px-4">
                          <div>
                            <p className="font-medium text-gray-900">{userItem.full_name}</p>
                            <p className="text-sm text-gray-600">@{userItem.username}</p>
                          </div>
                        </td>
                        <td className="py-3 px-4">
                          <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                            userItem.role === 'admin' ? 'bg-green-100 text-green-800' :
                            userItem.role === 'doctor' ? 'bg-blue-100 text-blue-800' :
                            'bg-orange-100 text-orange-800'
                          }`}>
                            {userItem.role}
                          </span>
                          {userItem.specialty && (
                            <p className="text-xs text-gray-500 mt-1">{userItem.specialty}</p>
                          )}
                        </td>
                        <td className="py-3 px-4 text-gray-600">{userItem.district || '-'}</td>
                        <td className="py-3 px-4">
                          <div className="text-sm">
                            <p className="text-gray-900">{userItem.phone}</p>
                            <p className="text-gray-600">{userItem.email}</p>
                            {user.role === 'admin' && (
                              <div className="text-xs text-blue-600 mt-1">
                                <button 
                                  onClick={() => handleViewPassword(userItem.id, userItem.username)}
                                  className="hover:underline"
                                  title="View Password"
                                >
                                  View Password
                                </button>
                              </div>
                            )}
                          </div>
                        </td>
                        <td className="py-3 px-4">
                          <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                            userItem.is_active ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                          }`}>
                            {userItem.is_active ? 'Active' : 'Inactive'}
                          </span>
                        </td>
                        <td className="py-3 px-4">
                          {/* Only show action buttons for admin users */}
                          {user.role === 'admin' ? (
                            <div className="flex space-x-2">
                              <button 
                                onClick={() => handleEditUser(userItem.id)}
                                className="text-blue-600 hover:text-blue-800 transition-colors"
                                title="Edit User"
                              >
                                <Edit className="w-4 h-4" />
                              </button>
                              <button 
                                onClick={() => handleToggleUserStatus(userItem.id, userItem.is_active, userItem.full_name)}
                                className={`transition-colors ${userItem.is_active ? 'text-orange-600 hover:text-orange-800' : 'text-green-600 hover:text-green-800'}`}
                                title={userItem.is_active ? 'Deactivate User' : 'Activate User'}
                              >
                                {userItem.is_active ? '🚫' : '✅'}
                              </button>
                              <button 
                                onClick={() => handleDeleteUser(userItem.id, userItem.full_name)}
                                className="text-red-600 hover:text-red-800 transition-colors"
                                title="Soft Delete User"
                                disabled={userItem.id === user.id} // Prevent self-deletion
                              >
                                <Trash2 className="w-4 h-4" />
                              </button>
                              <button 
                                onClick={() => handlePermanentDeleteUser(userItem.id, userItem.full_name)}
                                className="text-red-800 hover:text-red-900 transition-colors"
                                title="Permanent Delete User"
                                disabled={userItem.id === user.id} // Prevent self-deletion
                              >
                                💀
                              </button>
                            </div>
                          ) : (
                            <span className="text-gray-400 text-sm">Admin Only</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* Appointments Tab */}
        {activeTab === 'appointments' && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <h2 className="text-2xl font-bold text-gray-900">Appointment Management</h2>
              <button 
                onClick={exportAppointments}
                className="btn-secondary flex items-center space-x-2"
              >
                <Download className="w-4 h-4" />
                <span>Export Data</span>
              </button>
            </div>

            <div className="glass-card">
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
                          <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                            appointment.status === 'pending' ? 'bg-yellow-100 text-yellow-800' :
                            appointment.status === 'accepted' ? 'bg-green-100 text-green-800' :
                            appointment.status === 'completed' ? 'bg-blue-100 text-blue-800' :
                            'bg-red-100 text-red-800'
                          }`}>
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
                        
                        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 text-sm">
                          <div>
                            <p className="text-gray-600">Patient</p>
                            <p className="font-medium">
                              {appointment.patient?.age}y, {appointment.patient?.gender}
                            </p>
                          </div>
                          <div>
                            <p className="text-gray-600">Provider</p>
                            <p className="font-medium">{appointment.provider?.full_name}</p>
                          </div>
                          <div>
                            <p className="text-gray-600">Doctor</p>
                            <p className="font-medium">
                              {appointment.doctor?.full_name || 'Unassigned'}
                            </p>
                          </div>
                          <div>
                            <p className="text-gray-600">Created</p>
                            <p className="font-medium">{formatDate(appointment.created_at)}</p>
                          </div>
                        </div>
                      </div>

                      {/* Admin Actions */}
                      {user.role === 'admin' && (
                        <div className="ml-4 flex flex-col space-y-2">
                          <button 
                            onClick={() => handleEditAppointment(appointment.id)}
                            className="text-blue-600 hover:text-blue-800 transition-colors flex items-center space-x-1"
                            title="Edit Appointment"
                          >
                            <Edit className="w-4 h-4" />
                            <span className="text-sm">Edit</span>
                          </button>
                          <button 
                            onClick={() => handleDeleteAppointment(appointment.id, appointment.patient?.name)}
                            className="text-red-600 hover:text-red-800 transition-colors flex items-center space-x-1"
                            title="Delete Appointment"
                          >
                            <Trash2 className="w-4 h-4" />
                            <span className="text-sm">Delete</span>
                          </button>
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Reports Tab */}
        {activeTab === 'reports' && (
          <div className="space-y-6">
            <h2 className="text-2xl font-bold text-gray-900">Greenstar System Reports</h2>
            
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <div className="glass-card">
                <h3 className="text-xl font-semibold text-gray-900 mb-4">Monthly Statistics</h3>
                <div className="space-y-4">
                  <div className="flex justify-between items-center p-3 bg-green-50 rounded-lg">
                    <span className="text-gray-700">Total Calls This Month</span>
                    <span className="font-bold text-green-600">{appointments.length}</span>
                  </div>
                  <div className="flex justify-between items-center p-3 bg-red-50 rounded-lg">
                    <span className="text-gray-700">Emergency Calls</span>
                    <span className="font-bold text-red-600">{stats.emergencyAppointments}</span>
                  </div>
                  <div className="flex justify-between items-center p-3 bg-emerald-50 rounded-lg">
                    <span className="text-gray-700">Completed Consultations</span>
                    <span className="font-bold text-emerald-600">{stats.completedAppointments}</span>
                  </div>
                </div>
              </div>

              <div className="glass-card">
                <h3 className="text-xl font-semibold text-gray-900 mb-4">Provider Performance</h3>
                <div className="space-y-3">
                  {users.filter(u => u.role === 'provider').map((provider) => {
                    const providerAppts = appointments.filter(a => a.provider_id === provider.id);
                    return (
                      <div key={provider.id} className="flex justify-between items-center">
                        <div>
                          <p className="font-medium">{provider.full_name}</p>
                          <p className="text-sm text-gray-600">{provider.district}</p>
                        </div>
                        <span className="font-semibold">{providerAppts.length} calls</span>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>

            <div className="glass-card">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-xl font-semibold text-gray-900">Export Reports</h3>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <button 
                  onClick={exportMonthlyReport}
                  className="btn-secondary flex items-center justify-center space-x-2"
                >
                  <Download className="w-4 h-4" />
                  <span>Monthly Report</span>
                </button>
                <button 
                  onClick={exportUsers}
                  className="btn-secondary flex items-center justify-center space-x-2"
                >
                  <Download className="w-4 h-4" />
                  <span>User Report</span>
                </button>
                <button 
                  onClick={exportAppointments}
                  className="btn-secondary flex items-center justify-center space-x-2"
                >
                  <Download className="w-4 h-4" />
                  <span>Call Logs</span>
                </button>
              </div>
            </div>

            <div className="glass-card border-red-200 bg-red-50">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-xl font-semibold text-red-800">⚠️ System Maintenance</h3>
              </div>
              <div className="text-sm text-red-700 mb-4">
                <p className="mb-2">Use these functions with extreme caution. These operations cannot be undone.</p>
              </div>
              <div className="grid grid-cols-1 gap-4">
                <button 
                  onClick={handleCleanupAllAppointments}
                  className="bg-red-500 hover:bg-red-600 text-white px-4 py-3 rounded-lg font-semibold flex items-center justify-center space-x-2 transition-colors"
                >
                  <Trash2 className="w-4 h-4" />
                  <span>🗑️ Clean All Appointments</span>
                </button>
              </div>
              <div className="text-xs text-red-600 mt-2">
                <p>This will permanently remove all appointments, patient data, and consultation notes.</p>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Add User Modal */}
      {showAddUserForm && <AddUserForm />}

      {/* Edit Appointment Modal */}
      {showEditAppointmentModal && <EditAppointmentModal />}

      {/* Edit User Modal */}
      {showEditUserModal && <EditUserModal />}
    </div>
  );
};

export default AdminDashboard;