"""
Bootstrap script to set up admin user and verify accounts.
Usage: python scripts/bootstrap_admin.py <user_email> --make-admin --verify
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.user import User, UserRole
from app.db.session import Base


def get_db_session():
    """Create database session."""
    engine = create_engine(settings.DATABASE_URL)
    return Session(engine)


def make_admin(email: str):
    """Promote user to admin."""
    db = get_db_session()
    user = db.query(User).filter(User.email == email).first()
    
    if not user:
        print(f"❌ User with email '{email}' not found.")
        return False
    
    user.role = UserRole.ADMIN
    db.commit()
    print(f"✅ User '{email}' is now an ADMIN")
    print(f"   ID: {user.id}")
    print(f"   Role: {user.role.value}")
    return True


def verify_user(email: str):
    """Verify/activate user."""
    db = get_db_session()
    user = db.query(User).filter(User.email == email).first()
    
    if not user:
        print(f"❌ User with email '{email}' not found.")
        return False
    
    user.is_verified = True
    user.is_active = True
    db.commit()
    print(f"✅ User '{email}' is now VERIFIED and ACTIVE")
    print(f"   ID: {user.id}")
    print(f"   is_verified: {user.is_verified}")
    print(f"   is_active: {user.is_active}")
    return True


def list_users():
    """List all users."""
    db = get_db_session()
    users = db.query(User).order_by(User.created_at.desc()).all()
    
    if not users:
        print("No users found.")
        return
    
    print("\n📋 Users:")
    print("-" * 80)
    for user in users:
        status = "✅" if user.is_active else "❌"
        verified = "✓" if user.is_verified else "✗"
        print(f"{status} {user.email}")
        print(f"   ID: {user.id}")
        print(f"   Name: {user.full_name}")
        print(f"   Role: {user.role.value}")
        print(f"   Verified: {verified}")
        print()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/bootstrap_admin.py <email> [--make-admin] [--verify] [--list]")
        print("\nExamples:")
        print("  python scripts/bootstrap_admin.py sahilsoni.ds@gmail.com --make-admin --verify")
        print("  python scripts/bootstrap_admin.py sahilsoni.ds@gmail.com --make-admin")
        print("  python scripts/bootstrap_admin.py sahilsoni.ds@gmail.com --verify")
        print("  python scripts/bootstrap_admin.py --list")
        sys.exit(1)
    
    if sys.argv[1] == "--list":
        list_users()
    else:
        email = sys.argv[1]
        make_admin_flag = "--make-admin" in sys.argv
        verify_flag = "--verify" in sys.argv
        
        if not make_admin_flag and not verify_flag:
            list_users()
        else:
            if make_admin_flag:
                make_admin(email)
            if verify_flag:
                verify_user(email)
