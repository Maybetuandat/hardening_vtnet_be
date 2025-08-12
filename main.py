from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
import uvicorn

from routers import ssh_key_controller
# Import routers

app = FastAPI(title="Ansible Lab Runner API", version="1.0.0")

load_dotenv()
# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],  # Vite dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
HOST = os.getenv("SERVER_HOST")  
PORT = int(os.getenv("SERVER_PORT"))
RELOAD = os.getenv("SERVER_RELOAD", "False").lower() == "true"


# Include routers
app.include_router(ssh_key_controller.router, prefix="/ssh-keys", tags=["SSH Keys"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=HOST, port=PORT, reload=RELOAD)
