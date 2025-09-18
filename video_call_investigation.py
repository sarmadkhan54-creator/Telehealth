import requests
import json
from datetime import datetime

class VideoCallInvestigator:
    def __init__(self, base_url="https://calltrack-health.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.tokens = {}
        self.users = {}
        
        # Demo credentials
        self.demo_credentials = {
            "provider": {"username": "demo_provider", "password": "Demo123!"},
            "doctor": {"username": "demo_doctor", "password": "Demo123!"},
            "admin": {"username": "demo_admin", "password": "Demo123!"}
        }

    def login_all_users(self):
        """Login all users and store tokens"""
        print("🔑 Logging in all users...")
        for role, credentials in self.demo_credentials.items():
            try:
                response = requests.post(f"{self.api_url}/login", json=credentials, timeout=10)
                if response.status_code == 200:
                    data = response.json()
                    self.tokens[role] = data['access_token']
                    self.users[role] = data['user']
                    print(f"   ✅ {role.title()}: {data['user']['full_name']} (ID: {data['user']['id']})")
                else:
                    print(f"   ❌ {role.title()} login failed: {response.status_code}")
            except Exception as e:
                print(f"   ❌ {role.title()} login error: {str(e)}")

    def get_all_appointments(self):
        """Get appointments for each user role"""
        print("\n📅 Checking current appointments...")
        
        for role in ['admin', 'doctor', 'provider']:
            if role not in self.tokens:
                continue
                
            try:
                headers = {'Authorization': f'Bearer {self.tokens[role]}'}
                response = requests.get(f"{self.api_url}/appointments", headers=headers, timeout=10)
                
                if response.status_code == 200:
                    appointments = response.json()
                    print(f"\n   {role.upper()} sees {len(appointments)} appointments:")
                    
                    for apt in appointments:
                        status = apt.get('status', 'unknown')
                        apt_type = apt.get('appointment_type', 'unknown')
                        doctor_assigned = "Yes" if apt.get('doctor_id') else "No"
                        patient_name = apt.get('patient', {}).get('name', 'Unknown')
                        
                        print(f"     - ID: {apt['id'][:8]}... | Status: {status} | Type: {apt_type}")
                        print(f"       Patient: {patient_name} | Doctor Assigned: {doctor_assigned}")
                        
                        if apt.get('doctor'):
                            print(f"       Doctor: {apt['doctor']['full_name']}")
                        if apt.get('provider'):
                            print(f"       Provider: {apt['provider']['full_name']}")
                else:
                    print(f"   ❌ {role.title()} could not get appointments: {response.status_code}")
            except Exception as e:
                print(f"   ❌ {role.title()} appointments error: {str(e)}")

    def test_video_call_workflow_step_by_step(self):
        """Test the complete video call workflow as requested"""
        print("\n📹 Testing Video Call Workflow Step by Step...")
        
        # Step 1: Create a new appointment as provider
        print("\n   Step 1: Provider creates appointment...")
        appointment_data = {
            "patient": {
                "name": "Video Call Test Patient",
                "age": 40,
                "gender": "Male",
                "vitals": {
                    "blood_pressure": "130/85",
                    "heart_rate": 78,
                    "temperature": 98.8
                },
                "consultation_reason": "Video call workflow testing"
            },
            "appointment_type": "emergency",  # Test with emergency first
            "consultation_notes": "Testing video call workflow"
        }
        
        try:
            headers = {'Authorization': f'Bearer {self.tokens["provider"]}', 'Content-Type': 'application/json'}
            response = requests.post(f"{self.api_url}/appointments", json=appointment_data, headers=headers, timeout=10)
            
            if response.status_code == 200:
                appointment = response.json()
                appointment_id = appointment['id']
                print(f"     ✅ Created emergency appointment: {appointment_id}")
            else:
                print(f"     ❌ Failed to create appointment: {response.status_code}")
                return False
        except Exception as e:
            print(f"     ❌ Error creating appointment: {str(e)}")
            return False

        # Step 2: Doctor accepts the appointment
        print("\n   Step 2: Doctor accepts the appointment...")
        try:
            update_data = {
                "status": "accepted",
                "doctor_id": self.users['doctor']['id']
            }
            headers = {'Authorization': f'Bearer {self.tokens["doctor"]}', 'Content-Type': 'application/json'}
            response = requests.put(f"{self.api_url}/appointments/{appointment_id}", json=update_data, headers=headers, timeout=10)
            
            if response.status_code == 200:
                print(f"     ✅ Doctor accepted appointment")
            else:
                print(f"     ❌ Doctor failed to accept appointment: {response.status_code}")
                print(f"     Response: {response.text}")
                return False
        except Exception as e:
            print(f"     ❌ Error accepting appointment: {str(e)}")
            return False

        # Step 3: Doctor starts video call
        print("\n   Step 3: Doctor starts video call...")
        try:
            headers = {'Authorization': f'Bearer {self.tokens["doctor"]}'}
            response = requests.post(f"{self.api_url}/video-call/start/{appointment_id}", headers=headers, timeout=10)
            
            if response.status_code == 200:
                video_data = response.json()
                session_token = video_data['session_token']
                print(f"     ✅ Doctor started video call")
                print(f"     Session Token: {session_token}")
            else:
                print(f"     ❌ Doctor failed to start video call: {response.status_code}")
                print(f"     Response: {response.text}")
                return False
        except Exception as e:
            print(f"     ❌ Error starting video call: {str(e)}")
            return False

        # Step 4: Provider tries to join the call
        print("\n   Step 4: Provider tries to join the call...")
        try:
            headers = {'Authorization': f'Bearer {self.tokens["provider"]}'}
            response = requests.get(f"{self.api_url}/video-call/join/{session_token}", headers=headers, timeout=10)
            
            if response.status_code == 200:
                join_data = response.json()
                print(f"     ✅ Provider successfully joined video call")
                print(f"     Join Response: {json.dumps(join_data, indent=2)}")
            else:
                print(f"     ❌ Provider failed to join video call: {response.status_code}")
                print(f"     Response: {response.text}")
                return False
        except Exception as e:
            print(f"     ❌ Error joining video call: {str(e)}")
            return False

        # Step 5: Test with non-emergency appointment
        print("\n   Step 5: Testing with non-emergency appointment...")
        appointment_data['appointment_type'] = 'non_emergency'
        appointment_data['patient']['name'] = 'Non-Emergency Test Patient'
        
        try:
            headers = {'Authorization': f'Bearer {self.tokens["provider"]}', 'Content-Type': 'application/json'}
            response = requests.post(f"{self.api_url}/appointments", json=appointment_data, headers=headers, timeout=10)
            
            if response.status_code == 200:
                appointment2 = response.json()
                appointment_id2 = appointment2['id']
                print(f"     ✅ Created non-emergency appointment: {appointment_id2}")
                
                # Doctor accepts
                update_data = {
                    "status": "accepted",
                    "doctor_id": self.users['doctor']['id']
                }
                headers = {'Authorization': f'Bearer {self.tokens["doctor"]}', 'Content-Type': 'application/json'}
                response = requests.put(f"{self.api_url}/appointments/{appointment_id2}", json=update_data, headers=headers, timeout=10)
                
                if response.status_code == 200:
                    print(f"     ✅ Doctor accepted non-emergency appointment")
                    
                    # Doctor starts video call
                    headers = {'Authorization': f'Bearer {self.tokens["doctor"]}'}
                    response = requests.post(f"{self.api_url}/video-call/start/{appointment_id2}", headers=headers, timeout=10)
                    
                    if response.status_code == 200:
                        video_data2 = response.json()
                        session_token2 = video_data2['session_token']
                        print(f"     ✅ Doctor started video call for non-emergency")
                        
                        # Provider joins
                        headers = {'Authorization': f'Bearer {self.tokens["provider"]}'}
                        response = requests.get(f"{self.api_url}/video-call/join/{session_token2}", headers=headers, timeout=10)
                        
                        if response.status_code == 200:
                            print(f"     ✅ Provider joined non-emergency video call")
                        else:
                            print(f"     ❌ Provider failed to join non-emergency call: {response.status_code}")
                            print(f"     Response: {response.text}")
                    else:
                        print(f"     ❌ Doctor failed to start non-emergency video call: {response.status_code}")
                else:
                    print(f"     ❌ Doctor failed to accept non-emergency appointment: {response.status_code}")
            else:
                print(f"     ❌ Failed to create non-emergency appointment: {response.status_code}")
        except Exception as e:
            print(f"     ❌ Error with non-emergency workflow: {str(e)}")

        return True

    def test_provider_initiated_calls(self):
        """Test if providers can start calls and doctors can join"""
        print("\n🔄 Testing Provider-Initiated Video Calls...")
        
        # Get an existing accepted appointment
        try:
            headers = {'Authorization': f'Bearer {self.tokens["provider"]}'}
            response = requests.get(f"{self.api_url}/appointments", headers=headers, timeout=10)
            
            if response.status_code == 200:
                appointments = response.json()
                accepted_appointments = [apt for apt in appointments if apt.get('status') == 'accepted' and apt.get('doctor_id')]
                
                if accepted_appointments:
                    appointment_id = accepted_appointments[0]['id']
                    print(f"   Using accepted appointment: {appointment_id}")
                    
                    # Provider starts video call
                    print("   Provider starting video call...")
                    headers = {'Authorization': f'Bearer {self.tokens["provider"]}'}
                    response = requests.post(f"{self.api_url}/video-call/start/{appointment_id}", headers=headers, timeout=10)
                    
                    if response.status_code == 200:
                        video_data = response.json()
                        session_token = video_data['session_token']
                        print(f"     ✅ Provider started video call: {session_token}")
                        
                        # Doctor tries to join
                        print("   Doctor trying to join provider's call...")
                        headers = {'Authorization': f'Bearer {self.tokens["doctor"]}'}
                        response = requests.get(f"{self.api_url}/video-call/join/{session_token}", headers=headers, timeout=10)
                        
                        if response.status_code == 200:
                            print(f"     ✅ Doctor successfully joined provider's call")
                        else:
                            print(f"     ❌ Doctor failed to join provider's call: {response.status_code}")
                            print(f"     Response: {response.text}")
                    else:
                        print(f"     ❌ Provider failed to start video call: {response.status_code}")
                        print(f"     Response: {response.text}")
                else:
                    print("   ⚠️  No accepted appointments found for provider-initiated call test")
            else:
                print(f"   ❌ Failed to get appointments: {response.status_code}")
        except Exception as e:
            print(f"   ❌ Error testing provider-initiated calls: {str(e)}")

    def check_backend_logs_simulation(self):
        """Simulate checking backend logs by making detailed API calls"""
        print("\n📋 Checking Backend API Responses (Log Simulation)...")
        
        # Test various scenarios that might cause issues
        test_scenarios = [
            ("Invalid appointment ID", "video-call/start/invalid-id", "provider"),
            ("Missing authorization", "video-call/start/test-id", None),
            ("Invalid session token", "video-call/join/invalid-token", "provider"),
        ]
        
        for scenario_name, endpoint, token_override in test_scenarios:
            print(f"\n   Testing: {scenario_name}")
            try:
                headers = {}
                if token_override is None:
                    # No authorization header
                    pass
                elif token_override in self.tokens:
                    headers['Authorization'] = f'Bearer {self.tokens[token_override]}'
                
                if "start" in endpoint:
                    response = requests.post(f"{self.api_url}/{endpoint}", headers=headers, timeout=10)
                else:
                    response = requests.get(f"{self.api_url}/{endpoint}", headers=headers, timeout=10)
                
                print(f"     Status: {response.status_code}")
                print(f"     Response: {response.text[:200]}...")
                
            except Exception as e:
                print(f"     Error: {str(e)}")

def main():
    print("🔍 MedConnect Video Call Workflow Investigation")
    print("=" * 60)
    
    investigator = VideoCallInvestigator()
    
    # Step 1: Login all users
    investigator.login_all_users()
    
    # Step 2: Check current appointments
    investigator.get_all_appointments()
    
    # Step 3: Test complete workflow
    investigator.test_video_call_workflow_step_by_step()
    
    # Step 4: Test provider-initiated calls
    investigator.test_provider_initiated_calls()
    
    # Step 5: Check backend responses
    investigator.check_backend_logs_simulation()
    
    print("\n" + "=" * 60)
    print("🏁 Investigation Complete")

if __name__ == "__main__":
    main()