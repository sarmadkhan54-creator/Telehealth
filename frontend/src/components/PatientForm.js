import React, { useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import axios from 'axios';
import { ArrowLeft, User, Heart, Thermometer, Activity, Save } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const PatientForm = ({ user }) => {
  const navigate = useNavigate();
  const location = useLocation();
  const queryParams = new URLSearchParams(location.search);
  const appointmentType = queryParams.get('type') || 'non_emergency';

  const [formData, setFormData] = useState({
    name: '',
    age: '',
    gender: '',
    history: '',  // Replaced consultation_reason with history
    area_of_consultation: '',  // New field for area of consultation
    vitals: {
      blood_pressure: '',
      heart_rate: '',
      temperature: '',
      oxygen_saturation: '',
      weight: '',
      height: '',
      hb: '',  // New field: Hemoglobin (g/dL)
      sugar_level: ''  // New field: Blood Sugar (mg/dL)
    }
  });
  
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleChange = (e) => {
    const { name, value } = e.target;
    if (name.startsWith('vitals.')) {
      const vitalName = name.split('.')[1];
      setFormData(prev => ({
        ...prev,
        vitals: {
          ...prev.vitals,
          [vitalName]: value
        }
      }));
    } else {
      setFormData(prev => ({
        ...prev,
        [name]: value
      }));
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const appointmentData = {
        patient: {
          name: formData.name,
          age: parseInt(formData.age),
          gender: formData.gender,
          history: formData.history,  // Updated field name
          area_of_consultation: formData.area_of_consultation,  // New field
          vitals: formData.vitals
        },
        appointment_type: appointmentType,
        consultation_notes: ''
      };

      await axios.post(`${API}/appointments`, appointmentData);
      
      // Show success message
      alert(appointmentType === 'emergency' 
        ? 'Emergency appointment created! Doctors will be notified immediately.' 
        : 'Appointment created successfully!'
      );
      
      // Force refresh to show new appointment immediately
      window.location.href = '/';  // This will reload the dashboard and fetch new data
    } catch (error) {
      setError(error.response?.data?.detail || 'Failed to create appointment');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-green-50 to-emerald-100">
      {/* Header */}
      <nav className="nav-header">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <button
              onClick={() => navigate('/')}
              className="flex items-center space-x-2 px-3 py-2 text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
            >
              <ArrowLeft className="w-5 h-5" />
              <span>Back to Dashboard</span>
            </button>
            <div className="border-l border-gray-300 pl-3">
              <img 
                src="https://customer-assets.emergentagent.com/job_medconnect-app/artifacts/syacsqjj_Greenstar-Logo.png" 
                alt="Greenstar Healthcare" 
                className="h-8 w-auto object-contain"
              />
            </div>
          </div>
          
          <div className="text-right">
            <p className="font-semibold text-gray-900">{user.full_name}</p>
            <p className="text-sm text-gray-600">Provider</p>
          </div>
        </div>
      </nav>

      <div className="tablet-main">
        <div className="max-w-4xl mx-auto">
          <div className="glass-card">
            {/* Form Header */}
            <div className="text-center mb-8">
              <div className={`mx-auto flex items-center justify-center w-16 h-16 rounded-full mb-4 ${
                appointmentType === 'emergency' 
                  ? 'bg-gradient-to-br from-red-500 to-red-600' 
                  : 'bg-gradient-to-br from-green-500 to-green-600'
              }`}>
                <User className="w-8 h-8 text-white" />
              </div>
              <h2 className="text-3xl font-bold text-gray-900 mb-2">
                {appointmentType === 'emergency' ? 'Emergency' : 'Non-Emergency'} Appointment
              </h2>
              <p className="text-gray-600">
                Enter patient details and vitals for Greenstar consultation
              </p>
            </div>

            {error && (
              <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
                <p className="text-sm text-red-800">{error}</p>
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-8">
              {/* Patient Information */}
              <div>
                <h3 className="text-xl font-semibold text-gray-900 mb-4 flex items-center">
                  <User className="w-6 h-6 mr-2 text-green-600" />
                  Patient Information
                </h3>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div className="form-group">
                    <label htmlFor="name" className="form-label">Patient Name *</label>
                    <input
                      id="name"
                      name="name"
                      type="text"
                      required
                      className="form-input"
                      placeholder="Enter patient's full name"
                      value={formData.name}
                      onChange={handleChange}
                    />
                  </div>

                  <div className="form-group">
                    <label htmlFor="age" className="form-label">Age *</label>
                    <input
                      id="age"
                      name="age"
                      type="number"
                      required
                      min="0"
                      max="120"
                      className="form-input"
                      placeholder="Enter age"
                      value={formData.age}
                      onChange={handleChange}
                    />
                  </div>

                  <div className="form-group">
                    <label htmlFor="gender" className="form-label">Gender *</label>
                    <select
                      id="gender"
                      name="gender"
                      required
                      className="form-input"
                      value={formData.gender}
                      onChange={handleChange}
                    >
                      <option value="">Select gender</option>
                      <option value="male">Male</option>
                      <option value="female">Female</option>
                      <option value="other">Other</option>
                    </select>
                  </div>

                  {/* History Field - Vertically Stacked */}
                  <div className="form-group md:col-span-2">
                    <label htmlFor="history" className="form-label">
                      Patient History *
                    </label>
                    <textarea
                      id="history"
                      name="history"
                      required
                      rows={3}
                      maxLength={500}
                      className="form-input form-textarea"
                      placeholder="Describe the patient's medical history and current symptoms..."
                      value={formData.history}
                      onChange={handleChange}
                    />
                    <p className="text-xs text-gray-500 mt-1">
                      {formData.history.length}/500 characters
                    </p>
                  </div>

                  {/* Area of Consultation Field - Below History */}
                  <div className="form-group md:col-span-2">
                    <label htmlFor="area_of_consultation" className="form-label">
                      Area of Consultation *
                    </label>
                    <select
                      id="area_of_consultation"
                      name="area_of_consultation"
                      required
                      className="form-input"
                      value={formData.area_of_consultation}
                      onChange={handleChange}
                    >
                      <option value="">Select specialty area</option>
                      <option value="General Medical Services">⚕️ General Medical Services</option>
                      <option value="Family Medicine / Family Planning">👨‍👩‍👧‍👦 Family Medicine / Family Planning</option>
                      <option value="Pediatrics">👶 Pediatrics</option>
                      <option value="Neonatology">🍼 Neonatology</option>
                      <option value="Obstetrics & Gynaecology">🤱 Obstetrics & Gynaecology</option>
                      <option value="General Surgery">🔪 General Surgery</option>
                      <option value="Orthopaedics">🦴 Orthopaedics</option>
                      <option value="Emergency / Critical Care">🚨 Emergency / Critical Care</option>
                      <option value="Cardiology / Heart">🫀 Cardiology / Heart</option>
                      <option value="Pulmonology / Chest">🫁 Pulmonology / Chest</option>
                      <option value="Endocrinology & Diabetes">💉 Endocrinology & Diabetes</option>
                      <option value="Gastroenterology & Hepatology">🫄 Gastroenterology & Hepatology</option>
                      <option value="Nephrology / Kidney">🫘 Nephrology / Kidney</option>
                      <option value="Neurology / Brain & Spinal Cord">🧠 Neurology / Brain & Spinal Cord</option>
                      <option value="Rheumatology">🦴 Rheumatology</option>
                      <option value="Infectious Diseases">🦠 Infectious Diseases</option>
                      <option value="Dermatology / Skin">🌟 Dermatology / Skin</option>
                      <option value="Psychiatry & Mental Health">🧘‍♀️ Psychiatry & Mental Health</option>
                      <option value="Urology">🚰 Urology</option>
                      <option value="ENT (Ear, Nose, Throat)">👂 ENT (Ear, Nose, Throat)</option>
                      <option value="Ophthalmology / Eye">👁️ Ophthalmology / Eye</option>
                      <option value="Radiology & Imaging (X-ray, Ultrasound, CT, MRI)">📻 Radiology & Imaging (X-ray, Ultrasound, CT, MRI)</option>
                      <option value="Pathology & Laboratory">🧪 Pathology & Laboratory</option>
                      <option value="Physiotherapy & Rehabilitation">🏃‍♂️ Physiotherapy & Rehabilitation</option>
                      <option value="Nutrition & Dietetics">🥗 Nutrition & Dietetics</option>
                      <option value="Vaccination / Immunization">💉 Vaccination / Immunization</option>
                      <option value="Telehealth / Remote Consultation">💻 Telehealth / Remote Consultation</option>
                    </select>
                  </div>
                </div>
              </div>

              {/* Patient Vitals */}
              <div>
                <h3 className="text-xl font-semibold text-gray-900 mb-4 flex items-center">
                  <Activity className="w-6 h-6 mr-2 text-green-600" />
                  Patient Vitals (Optional)
                </h3>
                
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                  <div className="form-group">
                    <label htmlFor="vitals.blood_pressure" className="form-label flex items-center">
                      <Heart className="w-4 h-4 mr-1 text-red-500" />
                      Blood Pressure
                    </label>
                    <input
                      id="vitals.blood_pressure"
                      name="vitals.blood_pressure"
                      type="text"
                      className="form-input"
                      placeholder="e.g., 120/80"
                      value={formData.vitals.blood_pressure}
                      onChange={handleChange}
                    />
                  </div>

                  <div className="form-group">
                    <label htmlFor="vitals.heart_rate" className="form-label flex items-center">
                      <Heart className="w-4 h-4 mr-1 text-pink-500" />
                      Heart Rate (bpm)
                    </label>
                    <input
                      id="vitals.heart_rate"
                      name="vitals.heart_rate"
                      type="number"
                      className="form-input"
                      placeholder="e.g., 72"
                      value={formData.vitals.heart_rate}
                      onChange={handleChange}
                    />
                  </div>

                  <div className="form-group">
                    <label htmlFor="vitals.temperature" className="form-label flex items-center">
                      <Thermometer className="w-4 h-4 mr-1 text-orange-500" />
                      Temperature (°C)
                    </label>
                    <input
                      id="vitals.temperature"
                      name="vitals.temperature"
                      type="number"
                      step="0.1"
                      className="form-input"
                      placeholder="e.g., 37.0"
                      value={formData.vitals.temperature}
                      onChange={handleChange}
                    />
                  </div>

                  <div className="form-group">
                    <label htmlFor="vitals.oxygen_saturation" className="form-label flex items-center">
                      <Activity className="w-4 h-4 mr-1 text-blue-500" />
                      Oxygen Saturation (%)
                    </label>
                    <input
                      id="vitals.oxygen_saturation"
                      name="vitals.oxygen_saturation"
                      type="number"
                      min="0"
                      max="100"
                      className="form-input"
                      placeholder="e.g., 98"
                      value={formData.vitals.oxygen_saturation}
                      onChange={handleChange}
                    />
                  </div>

                  <div className="form-group">
                    <label htmlFor="vitals.weight" className="form-label">Weight (kg)</label>
                    <input
                      id="vitals.weight"
                      name="vitals.weight"
                      type="number"
                      step="0.1"
                      className="form-input"
                      placeholder="e.g., 70.5"
                      value={formData.vitals.weight}
                      onChange={handleChange}
                    />
                  </div>

                  <div className="form-group">
                    <label htmlFor="vitals.height" className="form-label">Height (cm)</label>
                    <input
                      id="vitals.height"
                      name="vitals.height"
                      type="number"
                      className="form-input"
                      placeholder="e.g., 175"
                      value={formData.vitals.height}
                      onChange={handleChange}
                    />
                  </div>

                  {/* New Vitals Fields */}
                  <div className="form-group">
                    <label htmlFor="vitals.hb" className="form-label flex items-center">
                      <span className="mr-1">💉</span>
                      Hemoglobin (g/dL)
                    </label>
                    <input
                      id="vitals.hb"
                      name="vitals.hb"
                      type="number"
                      step="0.1"
                      min="7"
                      max="18"
                      className={`form-input ${
                        formData.vitals.hb && (formData.vitals.hb < 7 || formData.vitals.hb > 18) 
                        ? 'border-red-500 bg-red-50' 
                        : formData.vitals.hb && formData.vitals.hb >= 7 && formData.vitals.hb <= 18
                        ? 'border-green-500 bg-green-50'
                        : ''
                      }`}
                      placeholder="e.g., 12.5"
                      value={formData.vitals.hb}
                      onChange={handleChange}
                    />
                    {formData.vitals.hb && (formData.vitals.hb < 7 || formData.vitals.hb > 18) && (
                      <p className="text-xs text-red-600 mt-1">
                        Normal range: 7-18 g/dL
                      </p>
                    )}
                  </div>

                  <div className="form-group">
                    <label htmlFor="vitals.sugar_level" className="form-label flex items-center">
                      <span className="mr-1">🍬</span>
                      Blood Sugar (mg/dL)
                    </label>
                    <input
                      id="vitals.sugar_level"
                      name="vitals.sugar_level"
                      type="number"
                      min="70"
                      max="200"
                      className={`form-input ${
                        formData.vitals.sugar_level && (formData.vitals.sugar_level < 70 || formData.vitals.sugar_level > 200) 
                        ? 'border-red-500 bg-red-50' 
                        : formData.vitals.sugar_level && formData.vitals.sugar_level >= 70 && formData.vitals.sugar_level <= 200
                        ? 'border-green-500 bg-green-50'
                        : ''
                      }`}
                      placeholder="e.g., 95"
                      value={formData.vitals.sugar_level}
                      onChange={handleChange}
                    />
                    {formData.vitals.sugar_level && (formData.vitals.sugar_level < 70 || formData.vitals.sugar_level > 200) && (
                      <p className="text-xs text-red-600 mt-1">
                        Normal range: 70-200 mg/dL
                      </p>
                    )}
                  </div>
                </div>
              </div>

              {/* Provider Information (Auto-filled) */}
              <div>
                <h3 className="text-xl font-semibold text-gray-900 mb-4">
                  Provider Information
                </h3>
                <div className="bg-green-50 rounded-lg p-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                    <div>
                      <p className="text-gray-600">Provider Name</p>
                      <p className="font-medium">{user.full_name}</p>
                    </div>
                    <div>
                      <p className="text-gray-600">District</p>
                      <p className="font-medium">{user.district}</p>
                    </div>
                    <div>
                      <p className="text-gray-600">Phone</p>
                      <p className="font-medium">{user.phone}</p>
                    </div>
                    <div>
                      <p className="text-gray-600">Email</p>
                      <p className="font-medium">{user.email}</p>
                    </div>
                  </div>
                </div>
              </div>

              {/* Submit Button */}
              <div className="flex justify-end space-x-4 pt-6">
                <button
                  type="button"
                  onClick={() => navigate('/')}
                  className="btn-secondary"
                >
                  Cancel
                </button>
                
                <button
                  type="submit"
                  disabled={loading}
                  className={`${appointmentType === 'emergency' ? 'btn-emergency' : 'btn-primary'} disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-2`}
                >
                  {loading ? (
                    <>
                      <div className="loading-spinner"></div>
                      <span>Creating...</span>
                    </>
                  ) : (
                    <>
                      <Save className="w-4 h-4" />
                      <span>
                        {appointmentType === 'emergency' ? 'Create Emergency Appointment' : 'Create Appointment'}
                      </span>
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
};

export default PatientForm;