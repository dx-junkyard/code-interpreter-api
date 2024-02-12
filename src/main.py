from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.routers import opendata_bridge_chat, opendata_bridge_runner, download, shutdown

app = FastAPI(root_path="/api")

origins = ["http://localhost:3000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(opendata_bridge_chat.router)
app.include_router(opendata_bridge_runner.router)
app.include_router(download.router)
app.include_router(shutdown.router)
