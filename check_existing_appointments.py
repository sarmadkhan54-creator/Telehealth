#!/usr/bin/env python3
"""
Check existing appointments to verify provider has accepted appointments to test with
"""

import requests
import json

def check_appointments():
    base_url = "https://telehealth-pwa.preview.emergentagent.com"
    api_url = f"{base_url}/api"
    
    # Login as provider
    login_data = {"username": "demo_provider", "password": "Demo123!"}
    response = requests.post(f"{api_url}/login", json=login_data)
    
    if response.status_code != 200:
        print("❌ Failed to login as provider")
        return
    
    token = response.json()['access_token']
    headers = {'Authorization': f'Bearer {token}'}
    
    # Get appointments
    response = requests.get(f"{api_url}/appointments", headers=headers)
    
    if response.status_code != 200:
        print("❌ Failed to get appointments")
        return
    
    appointments = response.json()
    
    print(f"📋 PROVIDER APPOINTMENTS SUMMARY")
    print(f"=" * 50)
    print(f"Total appointments: {len(appointments)}")
    
    accepted_appointments = [apt for apt in appointments if apt.get('status') == 'accepted']
    pending_appointments = [apt for apt in appointments if apt.get('status') == 'pending']
    
    print(f"Accepted appointments: {len(accepted_appointments)}")
    print(f"Pending appointments: {len(pending_appointments)}")
    
    if accepted_appointments:
        print(f"\n✅ ACCEPTED APPOINTMENTS (Ready for video calls):")
        for i, apt in enumerate(accepted_appointments, 1):
            patient_name = apt.get('patient', {}).get('name', 'Unknown')
            doctor_name = apt.get('doctor', {}).get('full_name', 'No doctor assigned')
            apt_type = apt.get('appointment_type', 'Unknown')
            apt_id = apt.get('id', 'Unknown')
            
            print(f"   {i}. Patient: {patient_name}")
            print(f"      Doctor: {doctor_name}")
            print(f"      Type: {apt_type}")
            print(f"      ID: {apt_id}")
            print(f"      🎬 Ready for 'Join Call' testing")
            print()
    
    if pending_appointments:
        print(f"\n⏳ PENDING APPOINTMENTS (Waiting for doctor):")
        for i, apt in enumerate(pending_appointments, 1):
            patient_name = apt.get('patient', {}).get('name', 'Unknown')
            apt_type = apt.get('appointment_type', 'Unknown')
            
            print(f"   {i}. Patient: {patient_name}")
            print(f"      Type: {apt_type}")
            print(f"      Status: Waiting for doctor acceptance")
            print()
    
    print(f"🎯 PROVIDER TESTING READY:")
    print(f"   • Login: demo_provider / Demo123!")
    print(f"   • {len(accepted_appointments)} accepted appointments available for video call testing")
    print(f"   • Look for 'Join Call' buttons on accepted appointments")

if __name__ == "__main__":
    check_appointments()