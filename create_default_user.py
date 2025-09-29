from passlib.context import CryptContext
from sqlalchemy.orm import Session
from models.user import User
from config.config_database import engine, SessionLocal

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def create_default_users():
    db = SessionLocal()
    try:
        # Danh sách user cần tạo
        users_data = [
            {
                "username": "admin",
                "email": "admin@company.com",
                "password": "admin123",
                "first_name": "System",
                "last_name": "Administrator",
                "role": "admin",
                "id_manager": None
            },
            {
                "username": "user1",
                "email": "john.doe@example.com",
                "password": "user123",
                "first_name": "John",
                "last_name": "Doe",
                "role": "user",
                "id_manager": 1
            },
            {
                "username": "user2",
                "email": "bob.wilson@example.com",
                "password": "user123",
                "first_name": "Bob",
                "last_name": "Wilson",
                "role": "user",
                "id_manager": 1
            },
            {
                "username": "user3",
                "email": "emma.brown@example.com",
                "password": "user123",
                "first_name": "Emma",
                "last_name": "Brown",
                "role": "user",
                "id_manager": 1
            },
            {
                "username": "user4",
                "email": "jane.smith@example.com",
                "password": "user123",
                "first_name": "Jane",
                "last_name": "Smith",
                "role": "user",
                "id_manager": 1
            },
            {
                "username": "user5",
                "email": "alice.jones@example.com",
                "password": "user123",
                "first_name": "Alice",
                "last_name": "Jones",
                "role": "user",
                "id_manager": 1
            }
        ]
        
        created_count = 0
        existing_count = 0
        
        for user_data in users_data:
            existing_user = db.query(User).filter(User.username == user_data["username"]).first()
            
            if not existing_user:
                password_hash = pwd_context.hash(user_data["password"])
                new_user = User(
                    username=user_data["username"],
                    email=user_data["email"],
                    password_hash=password_hash,
                    first_name=user_data["first_name"],
                    last_name=user_data["last_name"],
                    ssh_password="1",
                    role=user_data["role"],
                    id_manager=user_data["id_manager"],
                    is_active=True
                )
                db.add(new_user)
                created_count += 1
                print(f"✅ Created {user_data['username']}: {user_data['username']} / {user_data['password']}")
            else:
                existing_count += 1
                print(f"⚠️ {user_data['username']} already exists")
        
        db.commit()
        
        print(f"\n🎉 Process completed!")
        print(f"Created: {created_count} users")
        print(f"Already existed: {existing_count} users")
        print("\n📋 Login credentials:")
        print("- Admin: admin / admin123")
        print("- User1: user1 / user123 (John Doe)")
        print("- User2: user2 / user123 (Bob Wilson)")
        print("- User3: user3 / user123 (Emma Brown)")
        print("- User4: user4 / user123 (Jane Smith)")
        print("- User5: user5 / user123 (Alice Jones)")
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error creating users: {str(e)}")
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    create_default_users()