# main.py
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
import uvicorn


from config.config_database import engine, Base
from models import (

    workload, 
    server, 
    rule, 
    command, 
    compliance_result, 
    rule_result
)
from routers import command_controller, compliance_controller, dashboard_controller, rule_controller, rule_result_controller, server_controller, workload_controller

app = FastAPI(
    title="Ansible Security Scan API", 
    version="1.0.0",
    description="API for security compliance scanning using Ansible"
)

load_dotenv()


@app.on_event("startup")
async def startup_event():
    try:
        # Tạo tất cả bảng được định nghĩa trong models
        # SQLAlchemy sẽ tự động check và chỉ tạo table chưa có
        Base.metadata.create_all(bind=engine)
        print("✅ Database tables initialized successfully!")
        
        # Optional: Log tables được tạo
        table_names = list(Base.metadata.tables.keys())
        print(f"📋 Available tables: {table_names}")
        
        # Kiểm tra Ansible installation
        try:
            import subprocess
            result = subprocess.run(['ansible', '--version'], capture_output=True, text=True)
            if result.returncode == 0:
                print("✅ Ansible is installed and available")
                print(f"📋 Ansible version: {result.stdout.split()[0]} {result.stdout.split()[1]}")
            else:
                print("⚠️ Ansible is not installed or not accessible")
        except FileNotFoundError:
            print("⚠️ Ansible is not installed. Please install Ansible for full functionality")
        
    except Exception as e:
        print(f"❌ Error initializing application: {e}")
        # App vẫn có thể start, chỉ log error
        pass

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],  # Add more origins as needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

HOST = os.getenv("SERVER_HOST", "127.0.0.1")  
PORT = int(os.getenv("SERVER_PORT", 8000))
RELOAD = os.getenv("SERVER_RELOAD", "False").lower() == "true"

# Include routers

app.include_router(server_controller.router, tags=["Servers"])
app.include_router(workload_controller.router, tags=["Workloads"])
app.include_router(rule_controller.router, tags=["Rules"])
app.include_router(command_controller.router, tags=["Commands"])
app.include_router(compliance_controller.router, tags=["Compliance"])
app.include_router(rule_result_controller.router, tags=["Rule Results"])
app.include_router(dashboard_controller.router, tags=["Dashboard"])
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=HOST, port=PORT, reload=RELOAD)