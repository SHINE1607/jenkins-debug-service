from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.routes import router as api_router
from app.db.init_db import init_db
import asyncio
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"], 
    allow_headers=["*"],
    expose_headers=["*"]
)
app.include_router(api_router)

# include health check
@app.get("/", tags=["health"])
async def health_check():
    return {"message": "Hello World"}



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
