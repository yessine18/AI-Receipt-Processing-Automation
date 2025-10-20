"""
Script to create an admin user
"""
import sys
import os
from getpass import getpass

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.database import SessionLocal
from app.core.security import get_password_hash
from app.models.user import User


def create_admin():
    """Create an admin user"""
    db = SessionLocal()
    
    try:
        email = input("Enter admin email: ")
        full_name = input("Enter full name: ")
        password = getpass("Enter password: ")
        confirm_password = getpass("Confirm password: ")
        
        if password != confirm_password:
            print("Passwords do not match!")
            return
        
        # Check if user exists
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            print(f"User with email {email} already exists!")
            return
        
        # Create admin user
        admin = User(
            email=email,
            full_name=full_name,
            hashed_password=get_password_hash(password),
            is_admin=True,
            is_active=True
        )
        
        db.add(admin)
        db.commit()
        
        print(f"Admin user {email} created successfully!")
    
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    
    finally:
        db.close()


if __name__ == "__main__":
    create_admin()
