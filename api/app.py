from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette import status

from api.auth.auth_views import auth_router

api = FastAPI(
    title="ThemeCP Backend V2",
    description="This is the second version of ThemeCP backend",
    root_path="/api/v2",
    redoc_url="/docs",
)


api.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


api.include_router(auth_router)

@api.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    return {"status": "ok"}