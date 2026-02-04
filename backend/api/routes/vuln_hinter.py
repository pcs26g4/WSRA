from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException
from sqlalchemy.orm import Session
import uuid

from database.connection import get_db
from database.models import Scan, VulnerabilityHint
from agents.vuln_hinter import VulnHinterAgent

router = APIRouter(prefix="/scan", tags=["Vulnerabilities"])

@router.post("/{scan_id}/analyze-vulnerabilities")
async def trigger_vulnerability_analysis(
    scan_id: str, 
    background_tasks: BackgroundTasks, 
    db: Session = Depends(get_db)
):
    """
    Trigger the Vulnerability Hinter agent for a specific scan.
    """
    try:
        scan_uuid = uuid.UUID(scan_id)
        scan = db.query(Scan).filter(Scan.id == scan_uuid).first()
        if not scan:
            raise HTTPException(status_code=404, detail="Scan not found")
            
        agent = VulnHinterAgent(scan_id=scan_id)
        
        # Run appropriately (await directly since it's fast, or background if desired)
        # Given user request for "standalone" behavior but integrated, we can run it here and return results.
        hints = await agent.run(db)
        
        return {
            "status": "success",
            "message": "Vulnerability analysis completed",
            "hints_count": len(hints),
            "hints": hints
        }

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid Scan UUID")
    except Exception as e:
        logger.error(f"Vuln Analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{scan_id}/hints")
def get_vulnerability_hints(scan_id: str, db: Session = Depends(get_db)):
    """
    Retrieve generated vulnerability hints for a scan.
    """
    try:
        scan_uuid = uuid.UUID(scan_id)
        hints = db.query(VulnerabilityHint).filter(VulnerabilityHint.scan_id == scan_uuid).all()
        return hints
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid Scan UUID")
