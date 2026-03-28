#!/usr/bin/env python
"""
Email Verification Migration Script
Adds email verification fields to the User table
Run this script ONCE to add the email verification columns to your database
"""

def migrate_database():
    """Check email verification column status and guide correct migration."""
    print("=" * 60)
    print("Email Verification Migration Status Check")
    print("=" * 60)
    print()
    print("⚠  IMPORTANT: db.create_all() does NOT add columns to existing tables.")
    print("   SQLAlchemy's create_all() only creates tables that do not yet exist.")
    print("   It cannot ALTER an existing 'user' table to add new columns.")
    print()
    print("   To apply the email verification schema changes to an existing DB:")
    print()
    print("       flask db upgrade")
    print()
    print("   To set up a brand-new database from scratch, use:")
    print()
    print("       python init_db.py")
    print()
    try:
        from app import app
        from models import User
        with app.app_context():
            try:
                user_count = User.query.count()
                unverified_count = User.query.filter_by(is_email_verified=False).count()
                verified_count = User.query.filter_by(is_email_verified=True).count()
                print("✅ The email verification columns are present in your database.")
                print(f"   Total users:       {user_count}")
                print(f"   Verified users:    {verified_count}")
                print(f"   Unverified users:  {unverified_count}")
                if unverified_count > 0:
                    print()
                    print("⚠️  NOTICE:")
                    print(f"   {unverified_count} user(s) have not yet verified their email.")
                    print("   To grandfather all existing users, run:")
                    print("   python migrate_email_verification.py --grandfather-existing-users")
            except Exception as e:
                print(f"❌ Could not query email verification columns: {e}")
                print()
                print("   The columns likely do not exist yet. Run:")
                print()
                print("       flask db upgrade")
    except Exception as e:
        print(f"❌ Could not connect to the database: {e}")
        print()
        print("   Ensure your .env file is configured and your virtualenv is active,")
        print("   then run: flask db upgrade")

def grandfather_existing_users():
    """Mark all existing users as email verified."""
    print("=" * 60)
    print("Grandfathering Existing Users")
    print("=" * 60)
    
    try:
        from app import app, db
        from models import User
        from datetime import datetime, timezone
        
        with app.app_context():
            print("\n⏳ Marking existing users as email verified...")
            
            existing_users = User.query.filter_by(is_email_verified=False).all()
            count = len(existing_users)
            
            if count == 0:
                print("✅ All users are already verified!")
                return
            
            for user in existing_users:
                user.is_email_verified = True
                user.email_verified_at = datetime.now(timezone.utc)
                print(f"   ✓ Verified: {user.username} ({user.email})")
            
            db.session.commit()
            print(f"\n✅ Successfully verified {count} users!")
            print("   These users can now log in without email verification.")
            
    except Exception as e:
        print(f"\n❌ Grandfathering failed: {e}")
        raise

if __name__ == "__main__":
    import sys
    
    if "--grandfather-existing-users" in sys.argv:
        migrate_database()
        grandfather_existing_users()
    else:
        migrate_database()
    
    print("\n" + "=" * 60)
    print("Done! Your app is ready with email verification.")
    print("=" * 60)
