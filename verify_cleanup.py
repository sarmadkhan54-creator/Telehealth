#!/usr/bin/env python3
"""
Quick verification test to check if admin cleanup was successful
"""

import requests
import sys
import json

def verify_cleanup():
    base_url = "https://medconnect-live-1.preview.emergentagent.com"
    api_url = f"{base_url}/api"
    
    # Login as admin
    print("🔑 Logging in as admin...")
    login_response = requests.post(
        f"{api_url}/login",
        json={"username": "demo_admin", "password": "Demo123!"},
        timeout=10
    )
    
    if login_response.status_code != 200:
        print("❌ Admin login failed")
        return False
    
    admin_token = login_response.json()['access_token']
    print("✅ Admin login successful")
    
    # Check appointments
    print("\n📊 Checking appointments after cleanup...")
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {admin_token}'
    }
    
    appointments_response = requests.get(
        f"{api_url}/appointments",
        headers=headers,
        timeout=10
    )
    
    if appointments_response.status_code != 200:
        print("❌ Could not retrieve appointments")
        return False
    
    appointments = appointments_response.json()
    appointment_count = len(appointments) if isinstance(appointments, list) else 0
    
    print(f"📋 Found {appointment_count} appointments in database")
    
    if appointment_count == 0:
        print("✅ CLEANUP SUCCESSFUL: Database is clean!")
        print("🎯 Ready for new workflow testing without accept functionality")
        return True
    else:
        print(f"⚠️  {appointment_count} appointments still remain:")
        for i, apt in enumerate(appointments[:5]):
            print(f"   {i+1}. ID: {apt.get('id', 'N/A')[:20]}...")
            print(f"      Type: {apt.get('appointment_type', 'N/A')}")
            print(f"      Status: {apt.get('status', 'N/A')}")
        return False

if __name__ == "__main__":
    print("🧹 ADMIN CLEANUP VERIFICATION")
    print("=" * 50)
    
    try:
        success = verify_cleanup()
        if success:
            print("\n🎉 VERIFICATION PASSED: Cleanup was successful!")
            sys.exit(0)
        else:
            print("\n❌ VERIFICATION FAILED: Cleanup incomplete")
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error during verification: {str(e)}")
        sys.exit(1)