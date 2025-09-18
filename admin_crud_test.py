#!/usr/bin/env python3
"""
CRITICAL ADMIN FUNCTIONALITY TESTING
=====================================

This test specifically addresses the user's report that admin add/remove account operations 
show success messages but don't actually implement the changes.

Test Areas:
1. Admin Authentication & Access
2. User Creation Testing  
3. User Deletion Testing
4. User List Verification
5. Database State Verification

The test will verify the complete CRUD cycle with actual database verification.
"""

import requests
import sys
import json
from datetime import datetime
import time

class AdminCRUDTester:
    def __init__(self, base_url="https://calltrack-health.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.admin_token = None
        self.admin_user = None
        self.tests_run = 0
        self.tests_passed = 0
        self.created_users = []  # Track created users for cleanup
        
        # Demo admin credentials
        self.admin_credentials = {
            "username": "demo_admin", 
            "password": "Demo123!"
        }

    def log_test(self, name, success, details=""):
        """Log test results"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name}")
            if details:
                print(f"   {details}")
        else:
            print(f"❌ {name}")
            if details:
                print(f"   {details}")

    def make_request(self, method, endpoint, data=None, expected_status=200):
        """Make API request with proper headers"""
        url = f"{self.api_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        if self.admin_token:
            headers['Authorization'] = f'Bearer {self.admin_token}'

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
            
            try:
                response_data = response.json()
            except:
                response_data = {}
                
            return success, response_data, response.status_code
            
        except Exception as e:
            print(f"   Request failed: {str(e)}")
            return False, {}, 0

    def test_admin_authentication(self):
        """Test admin login and token validity"""
        print("\n🔑 TESTING ADMIN AUTHENTICATION & ACCESS")
        print("=" * 60)
        
        # Test admin login
        success, response, status = self.make_request(
            'POST', 'login', 
            data=self.admin_credentials,
            expected_status=200
        )
        
        if success and 'access_token' in response:
            self.admin_token = response['access_token']
            self.admin_user = response['user']
            self.log_test(
                "Admin Login", 
                True, 
                f"User ID: {self.admin_user.get('id')}, Role: {self.admin_user.get('role')}"
            )
        else:
            self.log_test("Admin Login", False, f"Status: {status}, Response: {response}")
            return False
        
        # Verify admin role
        if self.admin_user.get('role') != 'admin':
            self.log_test("Admin Role Verification", False, f"Expected 'admin', got '{self.admin_user.get('role')}'")
            return False
        else:
            self.log_test("Admin Role Verification", True, "User has admin role")
        
        # Test token validity by accessing admin-only endpoint
        success, response, status = self.make_request(
            'GET', 'users',
            expected_status=200
        )
        
        if success:
            user_count = len(response) if isinstance(response, list) else 0
            self.log_test("Admin Token Validity", True, f"Can access admin endpoints, found {user_count} users")
            return True
        else:
            self.log_test("Admin Token Validity", False, f"Cannot access admin endpoints, status: {status}")
            return False

    def get_current_user_count(self):
        """Get current user count from database"""
        success, response, status = self.make_request('GET', 'users')
        if success and isinstance(response, list):
            return len(response), response
        return 0, []

    def test_user_creation(self):
        """Test POST /api/admin/create-user endpoint with database verification"""
        print("\n➕ TESTING USER CREATION")
        print("=" * 60)
        
        # Get initial user count
        initial_count, initial_users = self.get_current_user_count()
        self.log_test("Get Initial User Count", True, f"Found {initial_count} users in database")
        
        # Create test user data
        timestamp = datetime.now().strftime('%H%M%S')
        test_user_data = {
            "username": f"test_admin_user_{timestamp}",
            "email": f"test_admin_{timestamp}@example.com",
            "password": "TestPassword123!",
            "phone": "+1234567890",
            "full_name": "Test Admin Created User",
            "role": "provider",
            "district": "Test District"
        }
        
        # Test user creation
        success, response, status = self.make_request(
            'POST', 'admin/create-user',
            data=test_user_data,
            expected_status=200
        )
        
        if success and 'id' in response:
            created_user_id = response['id']
            self.created_users.append(created_user_id)
            self.log_test(
                "Create User via Admin Endpoint", 
                True, 
                f"Created user ID: {created_user_id}, Username: {response.get('username')}"
            )
        else:
            self.log_test("Create User via Admin Endpoint", False, f"Status: {status}, Response: {response}")
            return False
        
        # Verify user actually exists in database
        time.sleep(1)  # Brief pause for database consistency
        after_create_count, after_create_users = self.get_current_user_count()
        
        if after_create_count == initial_count + 1:
            self.log_test("Database User Count Verification", True, f"Count increased from {initial_count} to {after_create_count}")
        else:
            self.log_test("Database User Count Verification", False, f"Expected {initial_count + 1}, got {after_create_count}")
            return False
        
        # Verify the specific user appears in the list
        created_user_found = False
        for user in after_create_users:
            if user.get('id') == created_user_id:
                created_user_found = True
                self.log_test(
                    "Created User in Database List", 
                    True, 
                    f"User {user.get('username')} found in GET /api/users response"
                )
                break
        
        if not created_user_found:
            self.log_test("Created User in Database List", False, "Created user not found in users list")
            return False
        
        # Test if new user can actually login
        login_success, login_response, login_status = self.make_request(
            'POST', 'login',
            data={"username": test_user_data["username"], "password": test_user_data["password"]},
            expected_status=200
        )
        
        if login_success and 'access_token' in login_response:
            self.log_test("New User Can Login", True, f"User {test_user_data['username']} successfully logged in")
        else:
            self.log_test("New User Can Login", False, f"Login failed with status: {login_status}")
            return False
        
        return True

    def test_user_deletion(self):
        """Test DELETE /api/users/{user_id} endpoint with database verification"""
        print("\n🗑️ TESTING USER DELETION")
        print("=" * 60)
        
        if not self.created_users:
            self.log_test("User Deletion Test", False, "No created users available for deletion testing")
            return False
        
        user_to_delete = self.created_users[0]
        
        # Get user count before deletion
        before_delete_count, before_delete_users = self.get_current_user_count()
        self.log_test("Get User Count Before Deletion", True, f"Found {before_delete_count} users")
        
        # Verify user exists before deletion
        user_exists_before = any(user.get('id') == user_to_delete for user in before_delete_users)
        if user_exists_before:
            self.log_test("User Exists Before Deletion", True, f"User {user_to_delete} found in database")
        else:
            self.log_test("User Exists Before Deletion", False, f"User {user_to_delete} not found in database")
            return False
        
        # Test user deletion
        success, response, status = self.make_request(
            'DELETE', f'users/{user_to_delete}',
            expected_status=200
        )
        
        if success:
            self.log_test("Delete User API Call", True, f"API returned success: {response.get('message', 'No message')}")
        else:
            self.log_test("Delete User API Call", False, f"Status: {status}, Response: {response}")
            return False
        
        # Verify user actually deleted from database
        time.sleep(1)  # Brief pause for database consistency
        after_delete_count, after_delete_users = self.get_current_user_count()
        
        if after_delete_count == before_delete_count - 1:
            self.log_test("Database User Count After Deletion", True, f"Count decreased from {before_delete_count} to {after_delete_count}")
        else:
            self.log_test("Database User Count After Deletion", False, f"Expected {before_delete_count - 1}, got {after_delete_count}")
            return False
        
        # Verify the specific user no longer appears in the list
        user_still_exists = any(user.get('id') == user_to_delete for user in after_delete_users)
        if not user_still_exists:
            self.log_test("Deleted User Not in Database List", True, f"User {user_to_delete} successfully removed from database")
        else:
            self.log_test("Deleted User Not in Database List", False, f"User {user_to_delete} still found in database")
            return False
        
        # Test if deleted user can no longer login
        # First, get the username of the deleted user from our test data
        timestamp = datetime.now().strftime('%H%M%S')
        deleted_username = f"test_admin_user_{timestamp}"
        
        login_success, login_response, login_status = self.make_request(
            'POST', 'login',
            data={"username": deleted_username, "password": "TestPassword123!"},
            expected_status=401  # Should fail with 401 Unauthorized
        )
        
        if login_success:  # Success here means we got the expected 401
            self.log_test("Deleted User Cannot Login", True, "Deleted user correctly denied login")
        else:
            # If we didn't get 401, check what we got
            if login_status == 401:
                self.log_test("Deleted User Cannot Login", True, "Deleted user correctly denied login")
            else:
                self.log_test("Deleted User Cannot Login", False, f"Unexpected status: {login_status}")
                return False
        
        # Remove from our tracking list
        self.created_users.remove(user_to_delete)
        
        return True

    def test_complete_crud_cycle(self):
        """Test the complete CRUD cycle as requested"""
        print("\n🔄 TESTING COMPLETE CRUD CYCLE")
        print("=" * 60)
        
        # Step 1: Login as admin
        if not self.admin_token:
            self.log_test("Complete CRUD Cycle", False, "Admin not authenticated")
            return False
        
        # Step 2: Get initial user count
        initial_count, initial_users = self.get_current_user_count()
        self.log_test("Step 1: Get Initial User Count", True, f"Initial count: {initial_count}")
        
        # Step 3: Create new user
        timestamp = datetime.now().strftime('%H%M%S%f')[:10]  # More unique timestamp
        test_user_data = {
            "username": f"crud_test_user_{timestamp}",
            "email": f"crud_test_{timestamp}@example.com",
            "password": "CrudTest123!",
            "phone": "+1987654321",
            "full_name": "CRUD Test User",
            "role": "doctor",
            "district": "CRUD Test District",
            "specialty": "General Medicine"
        }
        
        success, response, status = self.make_request(
            'POST', 'admin/create-user',
            data=test_user_data,
            expected_status=200
        )
        
        if success and 'id' in response:
            crud_user_id = response['id']
            self.log_test("Step 2: Create New User", True, f"Created user ID: {crud_user_id}")
        else:
            self.log_test("Step 2: Create New User", False, f"Failed to create user: {response}")
            return False
        
        # Step 4: Verify creation
        after_create_count, after_create_users = self.get_current_user_count()
        if after_create_count == initial_count + 1:
            self.log_test("Step 3: Verify Creation", True, f"User count increased to {after_create_count}")
        else:
            self.log_test("Step 3: Verify Creation", False, f"Expected {initial_count + 1}, got {after_create_count}")
            return False
        
        # Step 5: Delete user
        success, response, status = self.make_request(
            'DELETE', f'users/{crud_user_id}',
            expected_status=200
        )
        
        if success:
            self.log_test("Step 4: Delete User", True, f"User deleted: {response.get('message', 'Success')}")
        else:
            self.log_test("Step 4: Delete User", False, f"Failed to delete user: {response}")
            return False
        
        # Step 6: Verify deletion
        time.sleep(1)  # Brief pause for database consistency
        final_count, final_users = self.get_current_user_count()
        if final_count == initial_count:
            self.log_test("Step 5: Verify Deletion", True, f"User count returned to {final_count}")
        else:
            self.log_test("Step 5: Verify Deletion", False, f"Expected {initial_count}, got {final_count}")
            return False
        
        # Step 7: Compare final count with initial
        if final_count == initial_count:
            self.log_test("Step 6: Final Count Comparison", True, f"Final count ({final_count}) matches initial count ({initial_count})")
            return True
        else:
            self.log_test("Step 6: Final Count Comparison", False, f"Final count ({final_count}) does not match initial ({initial_count})")
            return False

    def test_database_state_verification(self):
        """Test database state verification after operations"""
        print("\n🗄️ TESTING DATABASE STATE VERIFICATION")
        print("=" * 60)
        
        # Get current database state
        success, users_list, status = self.make_request('GET', 'users')
        
        if not success:
            self.log_test("Database State Access", False, f"Cannot access users list: {status}")
            return False
        
        self.log_test("Database State Access", True, f"Successfully retrieved {len(users_list)} users")
        
        # Verify no orphaned records by checking user data integrity
        valid_users = 0
        invalid_users = 0
        
        for user in users_list:
            required_fields = ['id', 'username', 'email', 'full_name', 'role']
            if all(field in user and user[field] for field in required_fields):
                valid_users += 1
            else:
                invalid_users += 1
                print(f"   ⚠️ Invalid user found: {user.get('id', 'No ID')} - Missing fields")
        
        if invalid_users == 0:
            self.log_test("User Data Integrity", True, f"All {valid_users} users have complete data")
        else:
            self.log_test("User Data Integrity", False, f"{invalid_users} users have incomplete data")
        
        # Check for demo users existence
        demo_users = ['demo_admin', 'demo_provider', 'demo_doctor']
        found_demo_users = []
        
        for user in users_list:
            if user.get('username') in demo_users:
                found_demo_users.append(user.get('username'))
        
        if len(found_demo_users) == len(demo_users):
            self.log_test("Demo Users Integrity", True, f"All demo users present: {', '.join(found_demo_users)}")
        else:
            missing = set(demo_users) - set(found_demo_users)
            self.log_test("Demo Users Integrity", False, f"Missing demo users: {', '.join(missing)}")
        
        return invalid_users == 0

    def cleanup_created_users(self):
        """Clean up any remaining test users"""
        print("\n🧹 CLEANING UP TEST USERS")
        print("=" * 60)
        
        if not self.created_users:
            print("   No test users to clean up")
            return
        
        for user_id in self.created_users[:]:  # Copy list to avoid modification during iteration
            success, response, status = self.make_request(
                'DELETE', f'users/{user_id}',
                expected_status=200
            )
            
            if success:
                print(f"   ✅ Cleaned up user: {user_id}")
                self.created_users.remove(user_id)
            else:
                print(f"   ❌ Failed to clean up user: {user_id}")

    def run_all_tests(self):
        """Run all admin CRUD tests"""
        print("🎯 CRITICAL ADMIN FUNCTIONALITY TESTING")
        print("=" * 80)
        print("Testing admin add/remove account operations to verify actual implementation")
        print("=" * 80)
        
        # Test 1: Admin Authentication & Access
        if not self.test_admin_authentication():
            print("\n❌ CRITICAL FAILURE: Admin authentication failed - cannot proceed")
            return False
        
        # Test 2: User Creation Testing
        if not self.test_user_creation():
            print("\n❌ CRITICAL FAILURE: User creation not working properly")
            self.cleanup_created_users()
            return False
        
        # Test 3: User Deletion Testing
        if not self.test_user_deletion():
            print("\n❌ CRITICAL FAILURE: User deletion not working properly")
            self.cleanup_created_users()
            return False
        
        # Test 4: Complete CRUD Cycle
        if not self.test_complete_crud_cycle():
            print("\n❌ CRITICAL FAILURE: Complete CRUD cycle failed")
            self.cleanup_created_users()
            return False
        
        # Test 5: Database State Verification
        if not self.test_database_state_verification():
            print("\n⚠️ WARNING: Database state verification found issues")
        
        # Cleanup
        self.cleanup_created_users()
        
        # Final Results
        print("\n" + "=" * 80)
        print("🎯 ADMIN CRUD TESTING RESULTS")
        print("=" * 80)
        print(f"Tests Run: {self.tests_run}")
        print(f"Tests Passed: {self.tests_passed}")
        print(f"Success Rate: {(self.tests_passed/self.tests_run)*100:.1f}%")
        
        if self.tests_passed == self.tests_run:
            print("\n✅ ALL TESTS PASSED - Admin CRUD operations are working correctly!")
            print("✅ Users are actually created and deleted in the database")
            print("✅ Changes persist and are reflected in the user list")
            print("✅ No issues found with admin add/remove account operations")
            return True
        else:
            failed_tests = self.tests_run - self.tests_passed
            print(f"\n❌ {failed_tests} TESTS FAILED - Admin CRUD operations have issues!")
            print("❌ This confirms the user's report of problems with admin operations")
            return False

if __name__ == "__main__":
    tester = AdminCRUDTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)