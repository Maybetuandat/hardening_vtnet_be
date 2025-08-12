from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
import uvicorn

from routers import ssh_key_controller
from config.config_database import engine, Base
from models import ssh_key  # Import models để SQLAlchemy biết về chúng

# Import routers

app = FastAPI(title="Ansible Lab Runner API", version="1.0.0")

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
        
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        # App vẫn có thể start, chỉ log error
        pass

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[ "http://localhost:5173"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

HOST = os.getenv("SERVER_HOST", "127.0.0.1")  
PORT = int(os.getenv("SERVER_PORT", 8000))
RELOAD = os.getenv("SERVER_RELOAD", "False").lower() == "true"

# Include routers
app.include_router(ssh_key_controller.router, tags=["SSH Keys"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=HOST, port=PORT, reload=RELOAD)