# main.py
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
import uvicorn

from routers import server_controller, ssh_key_controller, workload_controller, scan_controller
from config.config_database import engine, Base
# Import tất cả models để SQLAlchemy biết về relationships
from models import (
    sshkey, 
    workload, 
    server, 
    rule, 
    command, 
    compliance_result, 
    rule_result, 
    security_standard
)

app = FastAPI(
    title="Ansible Security Scan API", 
    version="1.0.0",
    description="API for security compliance scanning using Ansible"
)

load_dotenv()

# Tạo tất cả bảng khi start app
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
app.include_router(ssh_key_controller.router, tags=["SSH Keys"])
app.include_router(workload_controller.router, tags=["Workloads"])
app.include_router(server_controller.router, tags=["Servers"])
app.include_router(scan_controller.router, tags=["Scan"])

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "Ansible Security Scan API",
        "version": "1.0.0"
    }

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Ansible Security Scan API",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc",
        "health": "/health"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=HOST, port=PORT, reload=RELOAD)