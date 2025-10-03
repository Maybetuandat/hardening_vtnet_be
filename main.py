from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
import logging

from config.config_database import engine, Base, get_db
from create_default_user import create_default_users
from routers import (
    auth_controller,
    compliance_result_controller,
    dashboard_controller,
    dcim_controller,
    export_controller,
    fix_controller,
    instance_controller,
    notification_controller,
    os_controller,
    rule_controller,
    rule_result_controller,
    schedule_controller,
    user_controller,
    workload_controller,
    rule_change_request_controller
)
from services.scheduler_singleton import SchedulerSingleton

# ===================== CONFIG APP =====================
app = FastAPI(
    title="Ansible Security Scan API",
    version="1.0.0",
    description="API for security compliance scanning using Ansible"
)

load_dotenv()
logger = logging.getLogger(__name__)

# ===================== STARTUP =====================
@app.on_event("startup")
async def startup_event():
    try:
        # DB init
        Base.metadata.create_all(bind=engine)
        print("✅ Database tables initialized successfully!")
        print(f"📋 Available tables: {list(Base.metadata.tables.keys())}")

        # Create default users
        try:
            create_default_users()
        except Exception as user_error:
            print(f"⚠️ Error creating default users: {user_error}")

        # Start Scheduler
        try:
            db = next(get_db())
            scheduler_instance = SchedulerSingleton.start_scheduler(db)
            debug_info = scheduler_instance.get_debug_info()
            print(f"🔍 Scheduler debug info: {debug_info}")
        except Exception as scheduler_error:
            print(f"⚠️ Error starting scheduler: {scheduler_error}")
            import traceback; traceback.print_exc()

        # Start External Notifier Worker
        try:
            from utils.external_notifier_worker import ExternalNotifierWorker
            from config.notifier_settings import get_notifier_settings

            settings = get_notifier_settings()
            worker = ExternalNotifierWorker.get_instance()
            worker.start()

            print("✅ External notifier worker started successfully")
            print(f"   - API URL: {settings.external_notifier_api_url}")
            print(f"   - Channel ID: {settings.external_notifier_channel_id}")
            print(f"   - Buffer Interval: {settings.external_notifier_buffer_interval}s")
        except Exception as notifier_error:
            print(f"❌ Error starting external notifier: {notifier_error}")
            import traceback; traceback.print_exc()

        # Start Scan Response Listener
        try:
            from listeners.scan_response_listener import ScanResponseListener
            listener = ScanResponseListener.get_instance()
            listener.start()
            print("✅ Scan response listener started successfully")
        except Exception as scan_listener_error:
            print(f"❌ Error starting scan response listener: {scan_listener_error}")
            import traceback; traceback.print_exc()

        # Check Ansible
        try:
            import subprocess
            result = subprocess.run(['ansible', '--version'], capture_output=True, text=True)
            if result.returncode == 0:
                print("✅ Ansible is installed and available")
        except FileNotFoundError:
            print("⚠️ Ansible is not installed")

    except Exception as e:
        print(f"❌ Error initializing application: {e}")
        import traceback; traceback.print_exc()


# ===================== SHUTDOWN =====================
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup khi tắt app"""
    # Stop Scheduler
    try:
        SchedulerSingleton.stop_scheduler()
        print("✅ Scheduler stopped successfully")
    except Exception as e:
        print(f"⚠️ Error stopping scheduler: {e}")

    # Stop External Notifier Worker
    try:
        from utils.external_notifier_worker import ExternalNotifierWorker
        worker = ExternalNotifierWorker.get_instance()
        if worker.is_running:
            worker.stop()
            print("✅ External notifier worker stopped successfully")

            stats = worker.get_stats()
            print(f"📊 Final notifier stats:")
            print(f"   - Total sent: {stats['total_sent']}")
            print(f"   - Total failed: {stats['total_failed']}")
            print(f"   - Total buffered: {stats['total_buffered']}")
        else:
            print("ℹ️ External notifier worker was not running")
    except Exception as e:
        print(f"⚠️ Error stopping external notifier: {e}")

    # Stop Scan Response Listener
    try:
        from listeners.scan_response_listener import ScanResponseListener
        listener = ScanResponseListener.get_instance()
        if listener.is_running:
            listener.stop()
            print("✅ Scan response listener stopped successfully")
    except Exception as e:
        print(f"⚠️ Error stopping scan response listener: {e}")


# ===================== MIDDLEWARE =====================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===================== ROUTERS =====================
app.include_router(instance_controller.router)
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
app.include_router(fix_controller.router)
app.include_router(dcim_controller.router)
app.include_router(rule_change_request_controller.router)

# ===================== RUN =====================
HOST = os.getenv("SERVER_HOST", "127.0.0.1")
PORT = int(os.getenv("SERVER_PORT", 8000))
RELOAD = os.getenv("SERVER_RELOAD", "False").lower() == "true"

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=HOST, port=PORT, reload=RELOAD)
