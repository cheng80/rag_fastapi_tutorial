from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import chat, documents, health, tourism
from app.core.config import PROJECT_ROOT, get_settings


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        description="무장애 관광 상담 챗봇 API",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router, prefix="/health", tags=["health"])
    app.include_router(chat.router, prefix="/chat", tags=["chat"])
    app.include_router(tourism.router, prefix="/tourism", tags=["tourism"])
    app.include_router(documents.router, prefix="/documents", tags=["documents"])

    web_frontend_path = PROJECT_ROOT / "frontend" / "web"
    if web_frontend_path.exists():
        app.mount(
            "/tourism-ui",
            StaticFiles(directory=web_frontend_path, html=True),
            name="tourism-ui",
        )

    return app


app = create_app()
