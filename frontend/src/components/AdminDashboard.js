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

const AdminDashboard = ({ user, onLogout }) => {
  const [activeTab, setActiveTab] = useState('overview');
  const [users, setUsers] = useState([]);
  const [appointments, setAppointments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showAddUserForm, setShowAddUserForm] = useState(false);

  // Admin access control - only allow admin users
  useEffect(() => {
    if (user.role !== 'admin') {
      alert('Access Denied: Only administrators can access this dashboard');
      onLogout();
      return;
    }
    fetchData();
  }, [user.role, onLogout]);

  const fetchData = async () => {
    try {
      const [usersResponse, appointmentsResponse] = await Promise.all([
        axios.get(`${API}/users`),
        axios.get(`${API}/appointments`)
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
        await axios.post(`${API}/register`, formData);
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
              <h1 className="nav-brand text-green-700">Greenstar Admin</h1>
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
              <button
                onClick={() => setShowAddUserForm(true)}
                className="btn-primary flex items-center space-x-2"
              >
                <UserPlus className="w-4 h-4" />
                <span>Add User</span>
              </button>
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
                    {users.map((user) => (
                      <tr key={user.id} className="border-b border-gray-100">
                        <td className="py-3 px-4">
                          <div>
                            <p className="font-medium text-gray-900">{user.full_name}</p>
                            <p className="text-sm text-gray-600">@{user.username}</p>
                          </div>
                        </td>
                        <td className="py-3 px-4">
                          <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                            user.role === 'admin' ? 'bg-green-100 text-green-800' :
                            user.role === 'doctor' ? 'bg-blue-100 text-blue-800' :
                            'bg-orange-100 text-orange-800'
                          }`}>
                            {user.role}
                          </span>
                          {user.specialty && (
                            <p className="text-xs text-gray-500 mt-1">{user.specialty}</p>
                          )}
                        </td>
                        <td className="py-3 px-4 text-gray-600">{user.district || '-'}</td>
                        <td className="py-3 px-4">
                          <div className="text-sm">
                            <p className="text-gray-900">{user.phone}</p>
                            <p className="text-gray-600">{user.email}</p>
                          </div>
                        </td>
                        <td className="py-3 px-4">
                          <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                            user.is_active ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                          }`}>
                            {user.is_active ? 'Active' : 'Inactive'}
                          </span>
                        </td>
                        <td className="py-3 px-4">
                          <div className="flex space-x-2">
                            <button className="text-blue-600 hover:text-blue-800">
                              <Edit className="w-4 h-4" />
                            </button>
                            <button className="text-red-600 hover:text-red-800">
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </div>
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
                            'bg-blue-100 text-blue-800'
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
          </div>
        )}
      </div>

      {/* Add User Modal */}
      {showAddUserForm && <AddUserForm />}
    </div>
  );
};

export default AdminDashboard;