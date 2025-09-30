#!/usr/bin/env python3

import sys
import inspect

# Import the class
from backend_test import MedConnectAPITester

# Create instance
tester = MedConnectAPITester()

# Check if method exists
method_name = 'test_focused_appointment_video_workflow'
has_method = hasattr(tester, method_name)

print(f"Method '{method_name}' exists: {has_method}")

if has_method:
    method = getattr(tester, method_name)
    print(f"Method is callable: {callable(method)}")
    print(f"Method signature: {inspect.signature(method)}")
else:
    print("Available methods:")
    methods = [method for method in dir(tester) if method.startswith('test_')]
    for method in sorted(methods):
        print(f"  - {method}")