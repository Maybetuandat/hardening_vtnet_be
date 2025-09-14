from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
import uvicorn
import logging

from config.config_database import engine, Base, get_db

from create_default_user import create_default_users
from routers import (
    
    auth_controller,
    compliance_result_controller, 
    dashboard_controller,
    export_controller,
    notification_controller,
    os_controller,
    
    rule_controller, 
    rule_result_controller, 
    schedule_controller,
    server_controller,
    user_controller, 
    workload_controller
)
from services.scheduler_singleton import SchedulerSingleton



app = FastAPI(
    title="Ansible Security Scan API", 
    version="1.0.0",
    description="API for security compliance scanning using Ansible"
)

load_dotenv()


@app.on_event("startup")
async def startup_event():
    try:
        # Tạo tất cả bảng
        Base.metadata.create_all(bind=engine)
        print("✅ Database tables initialized successfully!")
        
        table_names = list(Base.metadata.tables.keys())
        print(f"📋 Available tables: {table_names}")

        try:
            create_default_users()
        except Exception as user_error:
            print(f"⚠️ Error creating default users: {user_error}")
        
        
        try:
            db = next(get_db())
            scheduler_instance = SchedulerSingleton.start_scheduler(db)
            
            # Debug info
            debug_info = scheduler_instance.get_debug_info()
            print(f"🔍 Scheduler debug info: {debug_info}")
            
        except Exception as scheduler_error:
            print(f"⚠️ Error starting scheduler: {scheduler_error}")
            import traceback
            traceback.print_exc()
        
        # Kiểm tra Ansible
        try:
            import subprocess
            result = subprocess.run(['ansible', '--version'], capture_output=True, text=True)
            if result.returncode == 0:
                print("✅ Ansible is installed and available")
        except FileNotFoundError:
            print("⚠️ Ansible is not installed")
        
    except Exception as e:
        print(f"❌ Error initializing application: {e}")
        import traceback
        traceback.print_exc()


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup khi tắt app"""
    try:
        SchedulerSingleton.stop_scheduler()
    except Exception as e:
        print(f"⚠️ Error stopping scheduler: {e}")


# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

HOST = os.getenv("SERVER_HOST", "127.0.0.1")  
PORT = int(os.getenv("SERVER_PORT", 8000))
RELOAD = os.getenv("SERVER_RELOAD", "False").lower() == "true"

# Include routers
app.include_router(server_controller.router)
app.include_router(workload_controller.router)
app.include_router(rule_controller.router)

app.include_router(compliance_result_controller.router)
app.include_router(rule_result_controller.router)
app.include_router(dashboard_controller.router)
app.include_router(schedule_controller.router)
app.include_router(export_controller.router)
app.include_router(notification_controller.router)
app.include_router(os_controller.router)
app.include_router(auth_controller.router)
app.include_router(user_controller.router)



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=HOST, port=PORT, reload=RELOAD)