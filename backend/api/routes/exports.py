from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import FileResponse
import os
import logging
import uuid

from exports.report_generator import ReportGeneratorAgent
from exports.burp_exporter import BurpExporterAgent
from database.connection import SessionLocal
from database.models import Export

# Setup logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/scan/{scan_id}/export", tags=["Exports"])

@router.get("/json")
async def export_json(scan_id: str):
    try:
        # First ensure reports are generated (saves to DB)
        ReportGeneratorAgent().generate_reports(scan_id)
        
        # Now fetch from DB
        db = SessionLocal()
        try:
            export = db.query(Export).filter(Export.scan_id == uuid.UUID(scan_id), Export.format == "json").first()
            if not export:
                raise HTTPException(status_code=404, detail="JSON Report not found")
            return Response(content=export.content, media_type="application/json")
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Export JSON Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/markdown")
async def export_md(scan_id: str):
    try:
        ReportGeneratorAgent().generate_reports(scan_id)
        db = SessionLocal()
        try:
            export = db.query(Export).filter(Export.scan_id == uuid.UUID(scan_id), Export.format == "markdown").first()
            if not export:
                raise HTTPException(status_code=404, detail="Markdown Report not found")
            return Response(content=export.content, media_type="text/markdown")
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Export MD Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/csv")
async def export_csv(scan_id: str):
    try:
        ReportGeneratorAgent().generate_reports(scan_id)
        db = SessionLocal()
        try:
            export = db.query(Export).filter(Export.scan_id == uuid.UUID(scan_id), Export.format == "csv").first()
            if not export:
                raise HTTPException(status_code=404, detail="CSV Report not found")
            return Response(content=export.content, media_type="text/csv")
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Export CSV Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/burp")
async def export_burp(scan_id: str):
    try:
        BurpExporterAgent().export_scan(scan_id)
        db = SessionLocal()
        try:
            export = db.query(Export).filter(Export.scan_id == uuid.UUID(scan_id), Export.format == "xml").first()
            if not export:
                raise HTTPException(status_code=404, detail="Burp XML Export not found")
            return Response(content=export.content, media_type="application/xml")
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Export Burp Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/db/{format}")
async def get_export_from_db(scan_id: str, format: str):
    db = SessionLocal()
    try:
        export = db.query(Export).filter(
            Export.scan_id == uuid.UUID(scan_id),
            Export.format == format
        ).first()
        
        if not export:
             # Fallback: try generating them
             try:
                 ReportGeneratorAgent().generate_reports(scan_id)
                 export = db.query(Export).filter(Export.scan_id == uuid.UUID(scan_id), Export.format == format).first()
             except: pass
             
             if not export:
                raise HTTPException(status_code=404, detail="Export not found in database")
            
        media_types = {
            "json": "application/json",
            "csv": "text/csv",
            "markdown": "text/markdown",
            "xml": "application/xml"
        }
        
        return Response(
            content=export.content,
            media_type=media_types.get(format, "text/plain"),
            headers={"Content-Disposition": f"attachment; filename=report_{scan_id}.{format}"}
        )
    finally:
        db.close()
