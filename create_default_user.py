from passlib.context import CryptContext
from sqlalchemy.orm import Session
from models.user import User
from config.config_database import engine, SessionLocal

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_default_users():
    """Create default admin and user accounts"""
    db = SessionLocal()
    try:
        # Check if users already exist
        existing_admin = db.query(User).filter(User.username == "admin").first()
        existing_user1 = db.query(User).filter(User.username == "user1").first()
        existing_user2 = db.query(User).filter(User.username == "user2").first()
        
        # Create admin user
        if not existing_admin:
            admin_hash = pwd_context.hash("admin123")
            admin_user = User(
                username="admin",
                email="admin@company.com",
                password_hash=admin_hash,
                full_name="System Administrator",
                role="admin",
                is_active=True
            )
            db.add(admin_user)
            print("✅ Created admin user: admin / admin123")
        else:
            print("⚠️ Admin user already exists")
        
        # Create user1
        if not existing_user1:
            user1_hash = pwd_context.hash("user123")
            user1 = User(
                username="user1",
                email="user1@company.com",
                password_hash=user1_hash,
                full_name="Regular User 1",
                role="user",
                is_active=True
            )
            db.add(user1)
            print("✅ Created user1: user1 / user123")
        else:
            print("⚠️ User1 already exists")
        
        # Create user2
        if not existing_user2:
            user2_hash = pwd_context.hash("user123")
            user2 = User(
                username="user2",
                email="user2@company.com",
                password_hash=user2_hash,
                full_name="Regular User 2",
                role="user",
                is_active=True
            )
            db.add(user2)
            print("✅ Created user2: user2 / user123")
        else:
            print("⚠️ User2 already exists")
        
        db.commit()
        print("\n🎉 Default users created successfully!")
        print("Login credentials:")
        print("- Admin: admin / admin123")
        print("- User1: user1 / user123")
        print("- User2: user2 / user123")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error creating users: {str(e)}")
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    create_default_users()