#!/usr/bin/env python3
"""
Test script to verify password hashes in the users.csv file
"""
import csv
import os
from werkzeug.security import check_password_hash, generate_password_hash

# File path
USERS_CSV = os.path.join(os.path.dirname(__file__), 'storage', 'users.csv')

def test_password(email, password_to_test):
    """Test if a password matches the stored hash for a given email"""
    if not os.path.exists(USERS_CSV):
        print(f"Users CSV not found at: {USERS_CSV}")
        return False
    
    with open(USERS_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row['email'].strip() == email.strip():
                stored_hash = row['password_hash']
                print(f"Found user: {row['name']}")
                print(f"Stored hash: {stored_hash}")
                
                # Test the password
                if check_password_hash(stored_hash, password_to_test):
                    print(f"✓ Password is CORRECT!")
                    return True
                else:
                    print(f"✗ Password is INCORRECT!")
                    return False
    
    print(f"User with email {email} not found")
    return False

def reset_password(email, new_password):
    """Reset password for a user"""
    if not os.path.exists(USERS_CSV):
        print(f"Users CSV not found at: {USERS_CSV}")
        return False
    
    # Read all users
    users = []
    with open(USERS_CSV, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        users = list(reader)
    
    # Find and update the user
    user_found = False
    for row in users:
        if row['email'].strip() == email.strip():
            row['password_hash'] = generate_password_hash(new_password)
            user_found = True
            print(f"Password reset for user: {row['name']}")
            break
    
    if not user_found:
        print(f"User with email {email} not found")
        return False
    
    # Write back to CSV
    with open(USERS_CSV, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['id', 'name', 'email', 'password_hash', 'wallet_address']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(users)
    
    print(f"✓ Password has been reset successfully!")
    print(f"New password: {new_password}")
    return True

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  Test password: python test_password.py test <email> <password>")
        print("  Reset password: python test_password.py reset <email> <new_password>")
        print()
        print("Examples:")
        print("  python test_password.py test user@example.com mypassword")
        print("  python test_password.py reset user@example.com newpassword123")
        sys.exit(1)
    
    action = sys.argv[1]
    
    if action == 'test':
        if len(sys.argv) < 4:
            print("Usage: python test_password.py test <email> <password>")
            sys.exit(1)
        email = sys.argv[2]
        password = sys.argv[3]
        test_password(email, password)
    
    elif action == 'reset':
        if len(sys.argv) < 4:
            print("Usage: python test_password.py reset <email> <new_password>")
            sys.exit(1)
        email = sys.argv[2]
        new_password = sys.argv[3]
        reset_password(email, new_password)
    
    else:
        print(f"Unknown action: {action}")
        print("Use 'test' or 'reset'")
        sys.exit(1)

