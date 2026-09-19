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

if __name__ == "__main__":
    uvicorn.run("api.main:app", host=HOST, port=PORT, reload=True)
