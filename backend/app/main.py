from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.admin_leagues import router as admin_leagues_router
from app.api.auth import router as auth_router
from app.api.games import router as games_router
from app.api.health import router as health_router
from app.api.leaderboards import router as leaderboards_router
from app.api.players import router as players_router
from app.api.roster_import import router as roster_import_router
from app.api.roster_requests import router as roster_requests_router
from app.api.seasons import router as seasons_router
from app.api.teams import router as teams_router
from app.core.config import get_settings
from app.core.errors import ApiError, api_error_handler

settings = get_settings()

app = FastAPI(title="StatsCenter API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_exception_handler(ApiError, api_error_handler)

app.include_router(health_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(admin_leagues_router, prefix="/api/v1")
app.include_router(teams_router, prefix="/api/v1")
app.include_router(roster_import_router, prefix="/api/v1")
app.include_router(roster_requests_router, prefix="/api/v1")
app.include_router(games_router, prefix="/api/v1")
app.include_router(leaderboards_router, prefix="/api/v1")
app.include_router(players_router, prefix="/api/v1")
app.include_router(seasons_router, prefix="/api/v1")
