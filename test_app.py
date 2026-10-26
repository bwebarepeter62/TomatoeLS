"""
Tomato Leaf Scan — Root Test Runner Shim
========================================
Delegates test execution to the comprehensive test suite in:
    web-app/tests/test_app.py
"""

import os
import sys

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
TEST_DIR = os.path.join(ROOT_DIR, 'web-app', 'tests')
if TEST_DIR not in sys.path:
    sys.path.insert(0, TEST_DIR)

from test_app import run_tests

if __name__ == '__main__':
    run_tests()
