from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import asyncpg
import os
import logging
from contextlib import asynccontextmanager
import socket

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SurveyCreate(BaseModel):
    title: str
    description: Optional[str] = None

class SurveyResponse(BaseModel):
    id: int
    title: str
    description: Optional[str]
    created_at: datetime

class VoteCreate(BaseModel):
    survey_id: int
    user_id: str
    choice: str

class VoteResponse(BaseModel):
    id: int
    survey_id: int
    user_id: str
    choice: str
    created_at: datetime

class HealthResponse(BaseModel):
    status: str
    service: str
    server_id: str
    db_connected: bool
    timestamp: datetime

async def get_db_pool():
    """Создание пула соединений с PostgreSQL"""
    return await asyncpg.create_pool(
        host=os.getenv('DB_HOST', 'postgres-master'),
        port=int(os.getenv('DB_PORT', 5432)),
        user=os.getenv('DB_USER', 'postgres'),
        password=os.getenv('DB_PASSWORD', 'secret'),
        database=os.getenv('DB_NAME', 'appdb'),
        min_size=1,
        max_size=10,
        command_timeout=60
    )

pool = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global pool
    # Startup
    logger.info("Starting up...")
    pool = await get_db_pool()
    logger.info("Database pool created")
    yield
    # Shutdown
    logger.info("Shutting down...")
    if pool:
        await pool.close()
        logger.info("Database pool closed")

app = FastAPI(
    title="HA Survey App",
    description="High Availability Web Application with FastAPI",
    version="1.0.0",
    lifespan=lifespan
)

try:
    from prometheus_fastapi_instrumentator import Instrumentator
    Instrumentator().instrument(app).expose(app)
    logger.info("Prometheus metrics enabled")
except Exception as e:
    logger.warning(f"Prometheus not available: {e}")


@app.get("/", response_model=HealthResponse)
async def root():
    """Главный endpoint для проверки"""
    db_connected = False
    if pool:
        try:
            async with pool.acquire() as conn:
                await conn.execute("SELECT 1")
                db_connected = True
        except:
            pass
    
    return HealthResponse(
        status="running",
        service="HA Survey App",
        server_id=os.getenv('HOSTNAME', 'unknown'),
        db_connected=db_connected,
        timestamp=datetime.now()
    )

@app.get("/health")
async def health_check():
    """Health check для Nginx"""
    return {"status": "healthy", "server": os.getenv('HOSTNAME', 'unknown')}

@app.get("/test_nginx")
async def check_nginx():
    SERVER_ID = socket.gethostname()
    return {"server": SERVER_ID}

@app.post("/api/surveys", response_model=SurveyResponse, status_code=status.HTTP_201_CREATED)
async def create_survey(survey: SurveyCreate):
    """Создание нового опроса"""
    global pool
    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "INSERT INTO surveys (title, description) VALUES ($1, $2) RETURNING id, title, description, created_at",
                survey.title, survey.description
            )
            logger.info(f"Survey created: {survey.title}")
            return SurveyResponse(
                id=row['id'],
                title=row['title'],
                description=row['description'],
                created_at=row['created_at']
            )
    except Exception as e:
        logger.error(f"Error creating survey: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/surveys", response_model=List[SurveyResponse])
async def get_surveys():
    """Получение списка всех опросов"""
    global pool
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch("SELECT id, title, description, created_at FROM surveys ORDER BY created_at DESC")
            return [
                SurveyResponse(
                    id=row['id'],
                    title=row['title'],
                    description=row['description'],
                    created_at=row['created_at']
                ) for row in rows
            ]
    except Exception as e:
        logger.error(f"Error getting surveys: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/surveys/{survey_id}", response_model=SurveyResponse)
async def get_survey(survey_id: int):
    """Получение опроса по ID"""
    global pool
    try:
        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id, title, description, created_at FROM surveys WHERE id = $1",
                survey_id
            )
            if not row:
                raise HTTPException(status_code=404, detail="Survey not found")
            return SurveyResponse(
                id=row['id'],
                title=row['title'],
                description=row['description'],
                created_at=row['created_at']
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting survey {survey_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/votes", response_model=VoteResponse, status_code=status.HTTP_201_CREATED)
async def create_vote(vote: VoteCreate):
    """Отправка голоса за опрос"""
    global pool
    try:
        async with pool.acquire() as conn:
            survey = await conn.fetchrow("SELECT id FROM surveys WHERE id = $1", vote.survey_id)
            if not survey:
                raise HTTPException(status_code=404, detail="Survey not found")
            
            existing = await conn.fetchrow(
                "SELECT id FROM votes WHERE survey_id = $1 AND user_id = $2",
                vote.survey_id, vote.user_id
            )
            if existing:
                raise HTTPException(status_code=400, detail="User already voted in this survey")
            
            row = await conn.fetchrow(
                "INSERT INTO votes (survey_id, user_id, choice) VALUES ($1, $2, $3) RETURNING id, survey_id, user_id, choice, created_at",
                vote.survey_id, vote.user_id, vote.choice
            )
            
            logger.info(f"Vote created: survey={vote.survey_id}, user={vote.user_id}")
            return VoteResponse(
                id=row['id'],
                survey_id=row['survey_id'],
                user_id=row['user_id'],
                choice=row['choice'],
                created_at=row['created_at']
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating vote: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/surveys/{survey_id}/results")
async def get_results(survey_id: int):
    """Получение статистики голосования"""
    global pool
    try:
        async with pool.acquire() as conn:
            survey = await conn.fetchrow("SELECT id, title FROM surveys WHERE id = $1", survey_id)
            if not survey:
                raise HTTPException(status_code=404, detail="Survey not found")
            
            rows = await conn.fetch(
                "SELECT choice, COUNT(*) as count FROM votes WHERE survey_id = $1 GROUP BY choice",
                survey_id
            )
            
            stats = {row['choice']: row['count'] for row in rows}
            total_votes = sum(stats.values())
            
            return {
                "survey_id": survey_id,
                "survey_title": survey['title'],
                "results": stats,
                "total_votes": total_votes
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting results: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv('PORT', 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)