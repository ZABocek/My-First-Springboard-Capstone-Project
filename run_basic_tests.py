#!/usr/bin/env python
"""Test basic app functionality."""

from app import app, init_db
from models import db, User, Ingredient, Cocktail
import json

def test_app():
    """Test basic app endpoints."""
    
    # Initialize database
    init_db()
    
    # Create a test client
    client = app.test_client()
    
    print("\n=== Testing Flask App ===\n")
    
    # Test 1: Homepage redirect (should redirect to register)
    print("Test 1: GET / (homepage - should redirect to register)")
    response = client.get('/')
    print(f"  Status Code: {response.status_code}")
    print(f"  Expected: 302 (redirect)")
    print(f"  Result: {'PASS' if response.status_code == 302 else 'FAIL'}\n")
    
    # Test 2: Register page
    print("Test 2: GET /register")
    response = client.get('/register')
    print(f"  Status Code: {response.status_code}")
    print(f"  Expected: 200")
    print(f"  Result: {'PASS' if response.status_code == 200 else 'FAIL'}\n")
    
    # Test 3: Login page
    print("Test 3: GET /login")
    response = client.get('/login')
    print(f"  Status Code: {response.status_code}")
    print(f"  Expected: 200")
    print(f"  Result: {'PASS' if response.status_code == 200 else 'FAIL'}\n")
    
    # Test 4: User registration
    print("Test 4: POST /register (register new user)")
    response = client.post('/register', data={
        'username': 'testuser',
        'email': 'test@example.com',
        'password': 'testpass123',
        'confirm': 'testpass123'
    }, follow_redirects=False)
    print(f"  Status Code: {response.status_code}")
    print(f"  Expected: 302 (redirect after successful registration)")
    # Check if user was created
    with app.app_context():
        user = User.query.filter_by(username='testuser').first()
        user_exists = user is not None
    print(f"  User Created: {user_exists}")
    print(f"  Result: {'PASS' if user_exists else 'FAIL'}\n")
    
    # Test 5: User login
    if user_exists:
        print("Test 5: POST /login (login with test user)")
        response = client.post('/login', data={
            'username': 'testuser',
            'password': 'testpass123'
        }, follow_redirects=False)
        print(f"  Status Code: {response.status_code}")
        print(f"  Expected: 302 (redirect after successful login)")
        print(f"  Result: {'PASS' if response.status_code == 302 else 'FAIL'}\n")
    
    # Test 6: Test models - create an ingredient
    print("Test 6: Create an ingredient in database")
    with app.app_context():
        ingredient = Ingredient(name='Vodka')
        db.session.add(ingredient)
        db.session.commit()
        
        # Verify it was created
        check_ingredient = Ingredient.query.filter_by(name='Vodka').first()
        ingredient_exists = check_ingredient is not None
    print(f"  Ingredient Created: {ingredient_exists}")
    print(f"  Result: {'PASS' if ingredient_exists else 'FAIL'}\n")
    
    # Test 7: Test models - create a cocktail
    print("Test 7: Create a cocktail in database")
    with app.app_context():
        cocktail = Cocktail(name='Test Cocktail', instructions='Mix and serve')
        db.session.add(cocktail)
        db.session.commit()
        
        # Verify it was created
        check_cocktail = Cocktail.query.filter_by(name='Test Cocktail').first()
        cocktail_exists = check_cocktail is not None
    print(f"  Cocktail Created: {cocktail_exists}")
    print(f"  Result: {'PASS' if cocktail_exists else 'FAIL'}\n")
    
    print("=== Tests Completed ===\n")

if __name__ == '__main__':
    test_app()
