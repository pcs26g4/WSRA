from fastapi import APIRouter, HTTPException, Query
from database.connection import SessionLocal
from database.models import Scan

router = APIRouter(tags=["Utility"])

@router.get("/scans")
async def list_scans(limit: int = Query(50, le=100)):
    db = SessionLocal()
    try:
        scans = db.query(Scan).order_by(Scan.started_at.desc()).limit(limit).all()
        return [
            {
                "scan_id": str(s.id),
                "target": s.target_domain,
                "status": s.status,
                "created_at": s.started_at,
            }
            for s in scans
        ]
    finally:
        db.close()


