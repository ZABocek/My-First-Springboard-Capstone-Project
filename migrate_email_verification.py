#!/usr/bin/env python
"""
Email Verification Migration Script
Adds email verification fields to the User table
Run this script ONCE to add the email verification columns to your database
"""

def migrate_database():
    """Migrate database to add email verification columns."""
    print("=" * 60)
    print("Email Verification Database Migration")
    print("=" * 60)
    
    try:
        from app import app, db
        
        with app.app_context():
            print("\n📋 Starting database migration...")
            print("Creating tables with new email verification columns...")
            
            # Create all tables (this will add the new columns)
            db.create_all()
            
            print("✅ Database migration completed successfully!")
            print("\n📊 Summary:")
            print("   - Added 'is_email_verified' column (default: False)")
            print("   - Added 'email_verified_at' column (timestamp)")
            print("\n🔍 Checking existing users...")
            
            from models import User
            user_count = User.query.count()
            unverified_count = User.query.filter_by(is_email_verified=False).count()
            verified_count = User.query.filter_by(is_email_verified=True).count()
            
            print(f"   - Total users: {user_count}")
            print(f"   - Unverified: {unverified_count}")
            print(f"   - Verified: {verified_count}")
            
            if unverified_count > 0:
                print("\n⚠️  IMPORTANT:")
                print(f"   You have {unverified_count} existing users without verified emails.")
                print("   These users will need to verify their email before logging in.")
                print("\n   Alternative: To grandfather existing users, run:")
                print("   python migrate_database.py --grandfather-existing-users")
            
            print("\n✨ Migration complete! You can now:")
            print("   1. Test registration at /register")
            print("   2. Check verification emails")
            print("   3. Verify your email with the link")
            print("   4. Log in with verified account")
            
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        print("\nTroubleshooting:")
        print("   1. Ensure your app.py can be imported")
        print("   2. Check that Flask and SQLAlchemy are installed")
        print("   3. Verify DATABASE_URL is set correctly")
        raise

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
