import logging
import urllib3
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database.connection import engine, Base
import database.models

from api.routes.scan import router as scan_router, active_scans
from api.routes.summary import router as summary_router
from api.routes.exports import router as export_router
from api.routes.utilities import router as utility_router
from api.routes.vuln_hinter import router as vuln_hinter_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="WSRA – Web Security Recon Agent",
    version="2.2",
    description="Comprehensive web security reconnaissance and vulnerability scanning API",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {
        "service": "WSRA",
        "status": "running",
        "active_scans": len(active_scans),
        "docs": "/docs",
    }

@app.get("/health")
async def health_check():
    from database.connection import SessionLocal
    from sqlalchemy import text
    try:
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "database": str(e)}
    finally:
        db.close()

app.include_router(scan_router)
app.include_router(vuln_hinter_router)
app.include_router(export_router)
app.include_router(summary_router)
app.include_router(utility_router)
