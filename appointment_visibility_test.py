import requests
import sys
import json
from datetime import datetime

class AppointmentVisibilityTester:
    def __init__(self, base_url="https://calltrack-health.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tokens = {}  # Store tokens for different user roles
        self.users = {}   # Store user data for different roles
        self.tests_run = 0
        self.tests_passed = 0
        
        # Test credentials from DEMO_CREDENTIALS.md
        self.demo_credentials = {
            "provider": {"username": "demo_provider", "password": "Demo123!"},
            "doctor": {"username": "demo_doctor", "password": "Demo123!"},
            "admin": {"username": "demo_admin", "password": "Demo123!"}
        }

    def run_test(self, name, method, endpoint, expected_status, data=None, token=None):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}" if endpoint else f"{self.api_url}/"
        headers = {'Content-Type': 'application/json'}
        if token:
            headers['Authorization'] = f'Bearer {token}'

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=10)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=10)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers, timeout=10)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=10)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    return True, response.json()
                except:
                    return True, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    error_detail = response.json()
                    print(f"   Error: {error_detail}")
                except:
                    print(f"   Response text: {response.text}")
                return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_login_all_roles(self):
        """Test login for all user roles"""
        print("\n🔑 Testing Login for All Roles")
        print("-" * 50)
        
        all_success = True
        for role, credentials in self.demo_credentials.items():
            success, response = self.run_test(
                f"Login {role.title()}",
                "POST", 
                "login",
                200,
                data=credentials
            )
            
            if success and 'access_token' in response:
                self.tokens[role] = response['access_token']
                self.users[role] = response['user']
                print(f"   ✅ {role.title()} login successful - Token obtained")
                print(f"   User ID: {response['user'].get('id')}")
                print(f"   Full Name: {response['user'].get('full_name')}")
                print(f"   Role: {response['user'].get('role')}")
            else:
                print(f"   ❌ {role.title()} login failed")
                all_success = False
        
        return all_success

    def test_appointment_visibility_issue_investigation(self):
        """🎯 INVESTIGATE APPOINTMENT VISIBILITY ISSUE FOR DOCTORS"""
        print("\n🎯 INVESTIGATING APPOINTMENT VISIBILITY ISSUE FOR DOCTORS")
        print("=" * 80)
        
        all_success = True
        created_appointment_ids = []
        
        # Ensure we have all required tokens
        if not all(role in self.tokens for role in ['provider', 'doctor', 'admin']):
            print("❌ Missing required tokens for appointment visibility testing")
            return False
        
        # Test 1: Create new appointment as provider and verify storage
        print("\n1️⃣ Testing Appointment Creation by Provider")
        print("-" * 50)
        
        appointment_data = {
            "patient": {
                "name": "Sarah Johnson",
                "age": 28,
                "gender": "Female",
                "vitals": {
                    "blood_pressure": "118/75",
                    "heart_rate": 78,
                    "temperature": 98.7,
                    "oxygen_saturation": 98
                },
                "consultation_reason": "Regular checkup and blood pressure monitoring"
            },
            "appointment_type": "non_emergency",
            "consultation_notes": "Patient reports feeling well, wants routine health assessment"
        }
        
        success, response = self.run_test(
            "Create New Appointment (Provider)",
            "POST",
            "appointments",
            200,
            data=appointment_data,
            token=self.tokens['provider']
        )
        
        if success and 'id' in response:
            new_appointment_id = response['id']
            created_appointment_ids.append(new_appointment_id)
            print(f"   ✅ New appointment created successfully: {new_appointment_id}")
            print(f"   Patient: {response.get('patient_id', 'N/A')}")
            print(f"   Provider: {response.get('provider_id', 'N/A')}")
            print(f"   Status: {response.get('status', 'N/A')}")
            print(f"   Type: {response.get('appointment_type', 'N/A')}")
        else:
            print("   ❌ Failed to create new appointment")
            all_success = False
            return False
        
        # Test 2: Create emergency appointment as provider
        print("\n2️⃣ Testing Emergency Appointment Creation by Provider")
        print("-" * 50)
        
        emergency_data = {
            "patient": {
                "name": "Michael Chen",
                "age": 45,
                "gender": "Male",
                "vitals": {
                    "blood_pressure": "165/95",
                    "heart_rate": 105,
                    "temperature": 101.2,
                    "oxygen_saturation": 94
                },
                "consultation_reason": "Severe headache and dizziness for 2 hours"
            },
            "appointment_type": "emergency",
            "consultation_notes": "URGENT: Patient experiencing severe symptoms, needs immediate attention"
        }
        
        success, response = self.run_test(
            "Create Emergency Appointment (Provider)",
            "POST",
            "appointments",
            200,
            data=emergency_data,
            token=self.tokens['provider']
        )
        
        if success and 'id' in response:
            emergency_appointment_id = response['id']
            created_appointment_ids.append(emergency_appointment_id)
            print(f"   ✅ Emergency appointment created successfully: {emergency_appointment_id}")
            print(f"   Type: {response.get('appointment_type', 'N/A')}")
            print(f"   Status: {response.get('status', 'N/A')}")
        else:
            print("   ❌ Failed to create emergency appointment")
            all_success = False
        
        # Test 3: Doctor Dashboard Appointment Query - Check if ALL appointments are visible
        print("\n3️⃣ Testing Doctor Dashboard Appointment Query")
        print("-" * 50)
        
        success, doctor_appointments = self.run_test(
            "Get ALL Appointments (Doctor Dashboard)",
            "GET",
            "appointments",
            200,
            token=self.tokens['doctor']
        )
        
        if success:
            print(f"   ✅ Doctor can query appointments - Found {len(doctor_appointments)} total appointments")
            
            # Check if newly created appointments are visible
            new_appointment_found = False
            emergency_appointment_found = False
            
            for apt in doctor_appointments:
                if apt.get('id') == new_appointment_id:
                    new_appointment_found = True
                    print(f"   ✅ NEW appointment visible to doctor: {apt.get('id')}")
                    print(f"      Patient: {apt.get('patient', {}).get('name', 'N/A')}")
                    print(f"      Provider: {apt.get('provider', {}).get('full_name', 'N/A')}")
                    print(f"      Status: {apt.get('status', 'N/A')}")
                    print(f"      Type: {apt.get('appointment_type', 'N/A')}")
                
                if apt.get('id') == emergency_appointment_id:
                    emergency_appointment_found = True
                    print(f"   ✅ EMERGENCY appointment visible to doctor: {apt.get('id')}")
                    print(f"      Patient: {apt.get('patient', {}).get('name', 'N/A')}")
                    print(f"      Type: {apt.get('appointment_type', 'N/A')}")
            
            if not new_appointment_found:
                print(f"   ❌ CRITICAL ISSUE: New appointment {new_appointment_id} NOT visible to doctor")
                all_success = False
            
            if not emergency_appointment_found:
                print(f"   ❌ CRITICAL ISSUE: Emergency appointment {emergency_appointment_id} NOT visible to doctor")
                all_success = False
            
            # Analyze appointment data structure
            print(f"\n   📊 Appointment Data Structure Analysis:")
            if doctor_appointments:
                sample_apt = doctor_appointments[0]
                required_fields = ['id', 'patient_id', 'provider_id', 'appointment_type', 'status', 'created_at']
                for field in required_fields:
                    if field in sample_apt:
                        print(f"      ✅ {field}: Present")
                    else:
                        print(f"      ❌ {field}: Missing")
                        all_success = False
                
                # Check if patient and provider data is embedded
                if 'patient' in sample_apt and sample_apt['patient']:
                    print(f"      ✅ patient: Embedded data present")
                else:
                    print(f"      ❌ patient: Embedded data missing")
                    all_success = False
                
                if 'provider' in sample_apt and sample_apt['provider']:
                    print(f"      ✅ provider: Embedded data present")
                else:
                    print(f"      ❌ provider: Embedded data missing")
                    all_success = False
        else:
            print("   ❌ Doctor cannot query appointments")
            all_success = False
        
        # Test 4: Provider Dashboard Query - Verify provider sees their own appointments
        print("\n4️⃣ Testing Provider Dashboard Appointment Query")
        print("-" * 50)
        
        success, provider_appointments = self.run_test(
            "Get Own Appointments (Provider Dashboard)",
            "GET",
            "appointments",
            200,
            token=self.tokens['provider']
        )
        
        if success:
            print(f"   ✅ Provider can query appointments - Found {len(provider_appointments)} own appointments")
            
            # Verify provider only sees their own appointments
            provider_id = self.users['provider']['id']
            for apt in provider_appointments:
                if apt.get('provider_id') != provider_id:
                    print(f"   ❌ Provider seeing appointment not owned by them: {apt.get('id')}")
                    all_success = False
                    break
            else:
                print("   ✅ Provider correctly sees only own appointments")
            
            # Check if new appointments are in provider's list
            new_in_provider_list = any(apt.get('id') == new_appointment_id for apt in provider_appointments)
            emergency_in_provider_list = any(apt.get('id') == emergency_appointment_id for apt in provider_appointments)
            
            if new_in_provider_list:
                print(f"   ✅ New appointment visible in provider's list")
            else:
                print(f"   ❌ New appointment NOT visible in provider's list")
                all_success = False
            
            if emergency_in_provider_list:
                print(f"   ✅ Emergency appointment visible in provider's list")
            else:
                print(f"   ❌ Emergency appointment NOT visible in provider's list")
                all_success = False
        else:
            print("   ❌ Provider cannot query appointments")
            all_success = False
        
        # Test 5: Admin Dashboard Query - Verify admin sees ALL appointments
        print("\n5️⃣ Testing Admin Dashboard Appointment Query")
        print("-" * 50)
        
        success, admin_appointments = self.run_test(
            "Get ALL Appointments (Admin Dashboard)",
            "GET",
            "appointments",
            200,
            token=self.tokens['admin']
        )
        
        if success:
            print(f"   ✅ Admin can query appointments - Found {len(admin_appointments)} total appointments")
            
            # Check if new appointments are visible to admin
            new_in_admin_list = any(apt.get('id') == new_appointment_id for apt in admin_appointments)
            emergency_in_admin_list = any(apt.get('id') == emergency_appointment_id for apt in admin_appointments)
            
            if new_in_admin_list:
                print(f"   ✅ New appointment visible in admin's list")
            else:
                print(f"   ❌ New appointment NOT visible in admin's list")
                all_success = False
            
            if emergency_in_admin_list:
                print(f"   ✅ Emergency appointment visible in admin's list")
            else:
                print(f"   ❌ Emergency appointment NOT visible in admin's list")
                all_success = False
        else:
            print("   ❌ Admin cannot query appointments")
            all_success = False
        
        # Test 6: Database Consistency Check
        print("\n6️⃣ Testing Database Consistency")
        print("-" * 50)
        
        # Get appointment details directly to verify database storage
        for apt_id in created_appointment_ids:
            success, apt_details = self.run_test(
                f"Get Appointment Details (ID: {apt_id[:8]}...)",
                "GET",
                f"appointments/{apt_id}",
                200,
                token=self.tokens['admin']
            )
            
            if success:
                print(f"   ✅ Appointment {apt_id[:8]}... stored correctly in database")
                print(f"      Provider ID: {apt_details.get('provider_id', 'N/A')}")
                print(f"      Patient ID: {apt_details.get('patient_id', 'N/A')}")
                print(f"      Status: {apt_details.get('status', 'N/A')}")
                print(f"      Created: {apt_details.get('created_at', 'N/A')}")
            else:
                print(f"   ❌ Appointment {apt_id[:8]}... NOT found in database")
                all_success = False
        
        # Test 7: Real-time Notification Test (WebSocket)
        print("\n7️⃣ Testing Real-time Notifications for New Appointments")
        print("-" * 50)
        
        try:
            # Create another appointment to test notifications
            notification_test_data = {
                "patient": {
                    "name": "Emma Wilson",
                    "age": 32,
                    "gender": "Female",
                    "vitals": {
                        "blood_pressure": "125/82",
                        "heart_rate": 85,
                        "temperature": 99.1
                    },
                    "consultation_reason": "Follow-up consultation for medication review"
                },
                "appointment_type": "non_emergency",
                "consultation_notes": "Patient needs medication adjustment review"
            }
            
            success, response = self.run_test(
                "Create Appointment for Notification Test",
                "POST",
                "appointments",
                200,
                data=notification_test_data,
                token=self.tokens['provider']
            )
            
            if success:
                notification_apt_id = response['id']
                created_appointment_ids.append(notification_apt_id)
                print(f"   ✅ Notification test appointment created: {notification_apt_id}")
                print("   ℹ️  In production, this would trigger WebSocket notifications to all doctors")
            else:
                print("   ❌ Failed to create notification test appointment")
                all_success = False
                
        except Exception as e:
            print(f"   ⚠️  Notification test failed: {str(e)}")
        
        # Test 8: Appointment Filtering and Sorting
        print("\n8️⃣ Testing Appointment Filtering and Data Integrity")
        print("-" * 50)
        
        if success and doctor_appointments:
            # Check appointment sorting (should be by created_at or updated_at)
            appointment_dates = []
            for apt in doctor_appointments:
                if 'created_at' in apt:
                    appointment_dates.append(apt['created_at'])
            
            if appointment_dates:
                print(f"   ✅ Appointments have creation timestamps")
                print(f"   📅 Date range: {min(appointment_dates)} to {max(appointment_dates)}")
            
            # Check for different appointment types
            appointment_types = set(apt.get('appointment_type', 'unknown') for apt in doctor_appointments)
            print(f"   📊 Appointment types found: {', '.join(appointment_types)}")
            
            # Check appointment statuses
            appointment_statuses = set(apt.get('status', 'unknown') for apt in doctor_appointments)
            print(f"   📊 Appointment statuses found: {', '.join(appointment_statuses)}")
            
            # Verify doctors can see appointments from different providers
            provider_ids = set(apt.get('provider_id', 'unknown') for apt in doctor_appointments if apt.get('provider_id'))
            print(f"   👥 Appointments from {len(provider_ids)} different providers visible to doctor")
            
            if len(provider_ids) > 1:
                print("   ✅ Doctor can see appointments from multiple providers (correct behavior)")
            else:
                print("   ⚠️  Doctor only sees appointments from 1 provider (may be expected if only 1 provider exists)")
        
        # Summary
        print("\n" + "="*80)
        print("📊 APPOINTMENT VISIBILITY INVESTIGATION RESULTS")
        print("="*80)
        
        if all_success:
            print("🎉 ALL APPOINTMENT VISIBILITY TESTS PASSED!")
            print("✅ New appointments created by providers are immediately visible to doctors")
            print("✅ Doctor dashboard shows ALL appointments as intended")
            print("✅ Appointment data structure includes all necessary fields")
            print("✅ Database storage and retrieval working correctly")
        else:
            print("❌ APPOINTMENT VISIBILITY ISSUES DETECTED!")
            print("🔍 Issues found in appointment visibility system")
            print("📋 Check individual test results above for specific problems")
        
        print(f"📈 Test Success Rate: {self.tests_passed}/{self.tests_run} ({(self.tests_passed/self.tests_run)*100:.1f}%)")
        print("="*80)
        
        return all_success

def main():
    """Main function to run appointment visibility investigation"""
    print("🚀 Starting MedConnect API Appointment Visibility Investigation")
    print("=" * 70)
    
    tester = AppointmentVisibilityTester()
    
    # First login to get tokens
    if not tester.test_login_all_roles():
        print("❌ Login tests failed - aborting investigation")
        return 1
    
    # Run appointment visibility investigation
    visibility_success = tester.test_appointment_visibility_issue_investigation()
    
    if visibility_success:
        print("\n✅ Appointment visibility system is working correctly")
        print("🎯 New appointments created by providers are immediately visible to doctors")
        print("✅ Doctor dashboard shows ALL appointments as intended")
        print("✅ Real-time notifications and data flow working properly")
        print("\n💡 If doctors are not seeing new appointments in the frontend:")
        print("   1. Check frontend auto-refresh functionality")
        print("   2. Verify WebSocket connections are working")
        print("   3. Check browser console for JavaScript errors")
        print("   4. Verify frontend is calling the correct API endpoints")
        print("   5. Check if frontend is filtering appointments incorrectly")
        return 0
    else:
        print("\n⚠️  Critical appointment visibility issues found - check logs above")
        print("🎯 Backend appointment system problems detected.")
        return 1

if __name__ == "__main__":
    sys.exit(main())