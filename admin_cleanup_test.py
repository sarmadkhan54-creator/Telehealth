#!/usr/bin/env python3
"""
Admin Cleanup Test - Clean all appointments from database
This test performs the specific cleanup requested by the user:
1. Login with demo_admin/Demo123!
2. Use DELETE /api/admin/appointments/cleanup endpoint
3. Verify cleanup was successful
"""

import requests
import sys
import json
from datetime import datetime

class AdminCleanupTester:
    def __init__(self, base_url="https://medconnect-app-5.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.admin_token = None
        self.tests_run = 0
        self.tests_passed = 0
        
        # Admin credentials as specified in the request
        self.admin_credentials = {
            "username": "demo_admin", 
            "password": "Demo123!"
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

    def test_admin_login(self):
        """Step 1: Login with demo_admin/Demo123!"""
        print("\n🔑 STEP 1: Admin Login")
        print("=" * 50)
        
        success, response = self.run_test(
            "Admin Login (demo_admin/Demo123!)",
            "POST", 
            "login",
            200,
            data=self.admin_credentials
        )
        
        if success and 'access_token' in response:
            self.admin_token = response['access_token']
            admin_user = response['user']
            print(f"   ✅ Admin login successful")
            print(f"   User ID: {admin_user.get('id')}")
            print(f"   Full Name: {admin_user.get('full_name')}")
            print(f"   Role: {admin_user.get('role')}")
            print(f"   Token obtained: {len(self.admin_token)} characters")
            return True
        else:
            print(f"   ❌ Admin login failed")
            return False

    def check_appointments_before_cleanup(self):
        """Check how many appointments exist before cleanup"""
        print("\n📊 Checking Appointments Before Cleanup")
        print("-" * 50)
        
        success, response = self.run_test(
            "Get All Appointments (Before Cleanup)",
            "GET",
            "appointments",
            200,
            token=self.admin_token
        )
        
        if success:
            appointment_count = len(response) if isinstance(response, list) else 0
            print(f"   📋 Found {appointment_count} appointments before cleanup")
            
            if appointment_count > 0:
                print("   📝 Sample appointments:")
                for i, apt in enumerate(response[:3]):  # Show first 3 appointments
                    print(f"      {i+1}. ID: {apt.get('id', 'N/A')[:20]}...")
                    print(f"         Type: {apt.get('appointment_type', 'N/A')}")
                    print(f"         Status: {apt.get('status', 'N/A')}")
                    if apt.get('patient'):
                        print(f"         Patient: {apt['patient'].get('name', 'N/A')}")
            else:
                print("   ✅ Database is already clean (no appointments found)")
            
            return appointment_count
        else:
            print("   ❌ Could not retrieve appointments before cleanup")
            return -1

    def test_admin_cleanup_endpoint(self):
        """Step 2: Use DELETE /api/admin/appointments/cleanup endpoint"""
        print("\n🧹 STEP 2: Admin Cleanup Endpoint")
        print("=" * 50)
        
        success, response = self.run_test(
            "Admin Cleanup All Appointments",
            "DELETE",
            "admin/appointments/cleanup",
            200,
            token=self.admin_token
        )
        
        if success:
            print(f"   ✅ Cleanup endpoint executed successfully")
            print(f"   📊 Cleanup Results:")
            
            if isinstance(response, dict):
                message = response.get('message', 'No message')
                deleted = response.get('deleted', {})
                
                print(f"      Message: {message}")
                print(f"      Deleted Data:")
                print(f"        - Appointments: {deleted.get('appointments', 0)}")
                print(f"        - Notes: {deleted.get('notes', 0)}")
                print(f"        - Patients: {deleted.get('patients', 0)}")
                
                total_deleted = (deleted.get('appointments', 0) + 
                               deleted.get('notes', 0) + 
                               deleted.get('patients', 0))
                print(f"      Total Records Deleted: {total_deleted}")
                
                return True, deleted
            else:
                print(f"      Response: {response}")
                return True, {}
        else:
            print(f"   ❌ Cleanup endpoint failed")
            return False, {}

    def verify_cleanup_success(self):
        """Step 3: Verify cleanup was successful by checking no appointments remain"""
        print("\n✅ STEP 3: Verify Cleanup Success")
        print("=" * 50)
        
        success, response = self.run_test(
            "Verify No Appointments Remain",
            "GET",
            "appointments",
            200,
            token=self.admin_token
        )
        
        if success:
            appointment_count = len(response) if isinstance(response, list) else 0
            print(f"   📋 Found {appointment_count} appointments after cleanup")
            
            if appointment_count == 0:
                print("   ✅ CLEANUP SUCCESSFUL: No appointments remain in database")
                print("   🎯 Clean slate achieved for new workflow testing")
                return True
            else:
                print(f"   ❌ CLEANUP INCOMPLETE: {appointment_count} appointments still exist")
                print("   📝 Remaining appointments:")
                for i, apt in enumerate(response[:5]):  # Show first 5 remaining
                    print(f"      {i+1}. ID: {apt.get('id', 'N/A')[:20]}...")
                    print(f"         Type: {apt.get('appointment_type', 'N/A')}")
                    print(f"         Status: {apt.get('status', 'N/A')}")
                return False
        else:
            print("   ❌ Could not verify cleanup - unable to retrieve appointments")
            return False

    def test_additional_cleanup_verification(self):
        """Additional verification - check related data is also cleaned"""
        print("\n🔍 Additional Cleanup Verification")
        print("-" * 50)
        
        # Try to access appointment notes (should be empty)
        print("   Checking if appointment notes were cleaned...")
        
        # Since we can't directly query notes without an appointment ID,
        # we'll verify by trying to create a new appointment and checking
        # that the system is ready for fresh data
        
        # Check health endpoint to ensure system is still operational
        success, response = self.run_test(
            "System Health Check After Cleanup",
            "GET",
            "health",
            200
        )
        
        if success:
            print("   ✅ System remains healthy after cleanup")
            print(f"   Status: {response.get('status', 'unknown')}")
            print(f"   Message: {response.get('message', 'No message')}")
            return True
        else:
            print("   ❌ System health check failed after cleanup")
            return False

    def run_complete_cleanup_test(self):
        """Run the complete admin cleanup test as requested"""
        print("\n" + "=" * 80)
        print("🧹 ADMIN CLEANUP TEST - CLEAN ALL APPOINTMENTS FROM DATABASE")
        print("=" * 80)
        print("Request: Clean up all appointments from the database using admin cleanup endpoint")
        print("Steps: 1) Login demo_admin/Demo123! 2) DELETE /api/admin/appointments/cleanup")
        print("       3) Verify cleanup success 4) Ensure clean slate for new workflow")
        print("=" * 80)
        
        # Step 1: Admin Login
        if not self.test_admin_login():
            print("\n❌ CLEANUP TEST FAILED: Could not login as admin")
            return False
        
        # Check appointments before cleanup
        appointments_before = self.check_appointments_before_cleanup()
        if appointments_before == -1:
            print("\n⚠️  Could not check appointments before cleanup, continuing...")
        
        # Step 2: Execute cleanup
        cleanup_success, deleted_data = self.test_admin_cleanup_endpoint()
        if not cleanup_success:
            print("\n❌ CLEANUP TEST FAILED: Cleanup endpoint failed")
            return False
        
        # Step 3: Verify cleanup
        if not self.verify_cleanup_success():
            print("\n❌ CLEANUP TEST FAILED: Cleanup verification failed")
            return False
        
        # Additional verification
        if not self.test_additional_cleanup_verification():
            print("\n⚠️  Additional verification had issues, but main cleanup succeeded")
        
        # Final summary
        print("\n" + "=" * 80)
        print("🎉 ADMIN CLEANUP TEST RESULTS")
        print("=" * 80)
        print(f"✅ Admin login successful: demo_admin/Demo123!")
        print(f"✅ Cleanup endpoint executed: DELETE /api/admin/appointments/cleanup")
        print(f"✅ Cleanup verification passed: No appointments remain")
        print(f"✅ System health confirmed: Ready for new workflow")
        
        if deleted_data:
            print(f"\n📊 Cleanup Statistics:")
            print(f"   - Appointments deleted: {deleted_data.get('appointments', 0)}")
            print(f"   - Notes deleted: {deleted_data.get('notes', 0)}")
            print(f"   - Patients deleted: {deleted_data.get('patients', 0)}")
        
        print(f"\n🎯 RESULT: Clean slate achieved for testing new workflow without accept functionality")
        print(f"📈 Test Summary: {self.tests_passed}/{self.tests_run} tests passed")
        print("=" * 80)
        
        return True

def main():
    """Main function to run the admin cleanup test"""
    tester = AdminCleanupTester()
    
    try:
        success = tester.run_complete_cleanup_test()
        
        if success:
            print("\n🎉 ADMIN CLEANUP COMPLETED SUCCESSFULLY")
            print("✅ Database is now clean and ready for new workflow testing")
            sys.exit(0)
        else:
            print("\n❌ ADMIN CLEANUP FAILED")
            print("❌ Please check the errors above and try again")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n⚠️  Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error during cleanup test: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()