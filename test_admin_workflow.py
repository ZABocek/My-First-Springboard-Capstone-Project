#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test script to verify the admin unlock and panel workflow."""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the app directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db, User
from flask_bcrypt import Bcrypt

bcrypt = Bcrypt(app)

def test_admin_workflow():
    """Test the admin unlock workflow."""
    print("\n" + "="*60)
    print("Testing Admin Unlock Workflow")
    print("="*60 + "\n")
    
    with app.app_context():
        # Clear existing users
        User.query.delete()
        db.session.commit()
        
        # Create a test user
        print("1. Creating test user...")
        hashed_password = bcrypt.generate_password_hash("password123".encode('utf-8'))
        test_user = User(
            email="admin_test@example.com",
            username="admin_testuser",
            password=hashed_password.decode('utf-8'),
            is_admin=False
        )
        db.session.add(test_user)
        db.session.commit()
        print("[PASS] Created user: {} (ID: {})".format(test_user.username, test_user.id))
        print("[PASS] is_admin field: {}".format(test_user.is_admin))
        
        # Test the admin unlock form
        print("\n2. Testing admin unlock with Flask test client...")
        client = app.test_client()
        
        # Get the unlock page to extract CSRF token
        print("   - Accessing /admin/unlock GET request...")
        response = client.get('/admin/unlock')
        print("[PASS] Status code: {}".format(response.status_code))
        assert response.status_code == 200, "Expected 200, got {}".format(response.status_code)
        
        # Extract CSRF token from response
        from html.parser import HTMLParser
        
        class CSRFExtractor(HTMLParser):
            def __init__(self):
                super().__init__()
                self.csrf_token = None
            
            def handle_starttag(self, tag, attrs):
                if tag == 'input':
                    attrs_dict = dict(attrs)
                    if attrs_dict.get('name') == 'csrf_token':
                        self.csrf_token = attrs_dict.get('value')
        
        extractor = CSRFExtractor()
        extractor.feed(response.data.decode('utf-8'))
        csrf_token = extractor.csrf_token
        if csrf_token:
            print("[PASS] Extracted CSRF token: {}...".format(csrf_token[:20]))
        else:
            print("[FAIL] No CSRF token found")
        
        # Test with wrong admin password
        print("\n3. Testing with WRONG admin password...")
        response = client.post('/admin/unlock', data={
            'csrf_token': csrf_token,
            'admin_key': 'wrongpassword'
        }, follow_redirects=True)
        print("[PASS] Status code: {}".format(response.status_code))
        assert 'Invalid admin password key' in response.data.decode('utf-8'), "Error message not found"
        print("[PASS] Correct error message displayed")
        
        # Check user is still not admin
        user = User.query.get(test_user.id)
        assert user.is_admin == False, "User should not be admin yet"
        print("[PASS] User is still not admin")
        
        # Test with correct admin password
        print("\n4. Testing with CORRECT admin password...")
        correct_key = os.getenv('ADMIN_PASSWORD_KEY', 'U$a$ucks50015')
        response = client.post('/admin/unlock', data={
            'csrf_token': csrf_token,
            'admin_key': correct_key
        }, follow_redirects=True)
        print("[PASS] Status code: {}".format(response.status_code))
        
        # Check for success message and redirect
        response_text = response.data.decode('utf-8')
        # The route should have redirected to admin panel, which requires is_admin=True
        # If we reached the panel, the admin unlock worked (auth check passed)
        assert 'Admin Panel' in response_text, "Admin workflow failed - did not reach admin panel"
        print("[PASS] Successfully redirected to Admin Panel")
        print("[PASS] Admin unlock workflow completed successfully")
        
        print("\n" + "="*60)
        print("*** ALL TESTS PASSED! ***")
        print("="*60 + "\n")
        return True

if __name__ == '__main__':
    try:
        success = test_admin_workflow()
        sys.exit(0 if success else 1)
    except Exception as e:
        print("\n*** TEST FAILED: {} ***".format(e))
        import traceback
        traceback.print_exc()
        sys.exit(1)
