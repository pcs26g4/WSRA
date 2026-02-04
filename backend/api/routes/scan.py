from fastapi import APIRouter, BackgroundTasks, HTTPException
from uuid import uuid4
import uuid
from typing import Dict

from api.models import ScanRequest, ScanResponse
from agents.orchestrator import Orchestrator
from database.connection import SessionLocal
from database.models import Scan

router = APIRouter(prefix="/scan", tags=["Scan"])

# UX ONLY (same as old code)
active_scans: Dict[str, str] = {}

# --------------------------------------------------
# Background runner (IDENTICAL to old logic)
# --------------------------------------------------

import logging
logger = logging.getLogger(__name__)

async def run_scan_task(scan_id: str, target_url: str):
    active_scans[scan_id] = "RUNNING"
    try:
        orchestrator = Orchestrator(
            target_url=target_url,
            scan_id=scan_id,
        )
        await orchestrator.run()
        active_scans[scan_id] = "COMPLETED"
    except Exception as e:
        logger.exception(f"Scan {scan_id} failed with error: {e}")
        active_scans[scan_id] = "FAILED"

# --------------------------------------------------
# START SCAN (OLD BEHAVIOR PRESERVED)
# --------------------------------------------------

@router.post("/start", response_model=ScanResponse)
async def start_scan(req: ScanRequest, bg: BackgroundTasks):
    scan_id = str(uuid4())
    active_scans[scan_id] = "INITIALIZING"

    # Create the Scan record IMMEDIATELY in the DB
    db = SessionLocal()
    try:
        from urllib.parse import urlparse
        from datetime import datetime, timezone
        
        domain = urlparse(str(req.url)).netloc
        new_scan = Scan(
            id=scan_id,
            target_domain=domain,
            status="INITIALIZING",
            started_at=datetime.now(timezone.utc)
        )
        db.add(new_scan)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to create scan record: {e}")
    finally:
        db.close()

    bg.add_task(
        run_scan_task,
        scan_id,
        str(req.url),
    )

    return ScanResponse(
        scan_id=scan_id,
        status="started",
        message=f"Scan initialized for {req.url}",
    )

# --------------------------------------------------
# STATUS
# --------------------------------------------------

@router.get("/{scan_id}/status")
async def scan_status(scan_id: str):
    status = active_scans.get(scan_id)

    if not status:
        db = SessionLocal()
        try:
            scan = db.query(Scan).filter(Scan.id == scan_id).first()
            status = scan.status if scan else None
        finally:
            db.close()

    if not status:
        raise HTTPException(404, "Scan not found")

    return {"scan_id": scan_id, "status": status}

from database.models import (
    Scan, Url, HtmlPage, NetworkRequest, JsFile, Sitemap, Form, Parameter, 
    InteractionTarget, InteractionOutcome, Session_details, AuditLog, 
    ScanStatistics, LLMRequest, PageSnapshot, Export, VulnerabilityHint
)

@router.delete("/{scan_id}")
async def delete_scan(scan_id: str):
    db = SessionLocal()
    try:
        # Validate UUID
        try:
            scan_uuid = uuid.UUID(scan_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid Scan ID format")

        # 1. Check existence (optional, but good for reporting)
        exists = db.query(Scan).filter(Scan.id == scan_uuid).count() > 0

        if not exists:
             return {"message": "Scan cleanup performed (scan was already missing from DB)"}

        # 2. DEFINITIVE LIST of all child models to clean manually
        # This is required because models.py does not implement cascade='all, delete-orphan'
        models_to_clean = [
            VulnerabilityHint, Export, Url, HtmlPage, NetworkRequest, JsFile, 
            Sitemap, Form, Parameter, InteractionTarget, InteractionOutcome, 
            Session_details, AuditLog, ScanStatistics, LLMRequest, PageSnapshot
        ]
        
        # 3. Execute Manual Bulk Deletes for Children
        for model in models_to_clean:
            db.query(model).filter(model.scan_id == scan_uuid).delete(synchronize_session=False)
        
        # 4. Execute Delete for Parent Scan
        db.query(Scan).filter(Scan.id == scan_uuid).delete(synchronize_session=False)
            
        db.commit()
        
        # 5. Clean up memory status
        if scan_id in active_scans:
            del active_scans[scan_id]
            
        return {"message": "Scan and all associated data deleted successfully"}

    except Exception as e:
        db.rollback()
        import traceback
        traceback.print_exc()
        raise HTTPException(500, detail=f"Delete failed: {str(e)}")
    finally:
        db.close()
