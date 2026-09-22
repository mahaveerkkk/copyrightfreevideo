import os
import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from api.routes import router
from api.config import HOST, PORT, BASE_DIR

app = FastAPI(
    title="Anti-Copyright & Video Transformation Platform",
    version="2.0.0",
    description="High-Throughput Perceptual Video Transformation Engine"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routes
app.include_router(router, prefix="/api")

# Mount Web UI static assets
web_dir = os.path.join(BASE_DIR, "web")
if os.path.exists(web_dir):
    app.mount("/", StaticFiles(directory=web_dir, html=True), name="static")

import threading
import time

def start_cleaner_background():
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    inputs_dir = os.path.join(base, "storage", "inputs")
    outputs_dir = os.path.join(base, "storage", "outputs")
    temp_dir = os.path.join(base, "storage", "temp")
    from core.cleaner_daemon import cleanup_old_files
    while True:
        try:
            # Clean temporary chunks and inputs older than 1 hour (3600s)
            cleanup_old_files([inputs_dir, temp_dir], max_age_seconds=3600)
            # Keep finished renders for 24 hours (86400s) so users can return & download anytime
            cleanup_old_files([outputs_dir], max_age_seconds=86400)
        except Exception as e:
            print("Cleaner error:", e)
        time.sleep(300)

@app.on_event("startup")
def on_startup():
    t = threading.Thread(target=start_cleaner_background, daemon=True)
    t.start()

if __name__ == "__main__":
    uvicorn.run("api.main:app", host=HOST, port=PORT, reload=True)
