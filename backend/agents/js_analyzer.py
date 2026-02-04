import asyncio
import json
import os
import subprocess
from typing import List, Dict, Any, Optional
import uuid
from sqlalchemy.orm import Session
from sqlalchemy import select
 
from database.connection import SessionLocal
from database.models import JsFile, Parameter, LLMRequest, Scan
import logging
import shutil

logger = logging.getLogger("js_analyzer")
 
class JSAnalyzerAgent:
    """Agent responsible for analyzing JavaScript files"""
   
    def __init__(self, scan_id: str, llm_enabled: bool = True):
        from llm.gemini_client import LLMClient
        from config.settings import settings
        self.scan_id = scan_id
        self.llm_enabled = llm_enabled
        self.llm = LLMClient(
            enabled=llm_enabled,
            agent_name="JSAnalyzer",
            model_name=settings.LLM_MODEL_JS
        )
        self.ast_script_path = os.path.join(
            os.path.dirname(__file__), "js_parser", "ast_analysis.js"
        )
        self.node_available = shutil.which("node") is not None
        if not self.node_available:
            logger.warning("Node.js not found in PATH. AST analysis will be disabled.")
       
    async def analyze_latest_files(self, db: Session):
        """Analyze all pending JS files for the current scan"""
        try:
            # Query files that haven't been analyzed (sources is None)
            from database.models import JsFile
            
            pending_files = db.query(JsFile).filter(
                JsFile.scan_id == uuid.UUID(self.scan_id),
                JsFile.sources == None
            ).all()

            if not pending_files:
                return

            logger.info(f"🔍 Analyzing {len(pending_files)} new JS files...")

            for js_file in pending_files:
                if not js_file.content:
                    continue
                
                await self.analyze_file(
                    file_id=str(js_file.id),
                    url=js_file.url,
                    content=js_file.content
                )
        except Exception as e:
            logger.error(f"Batch JS analysis failed: {e}")

    async def analyze_file(self, file_id: str, url: str, content: str):
        """Analyze a single JavaScript file"""
        try:
            analysis_result = await self._analyze_with_ast(content)
           
            if not analysis_result:
                analysis_result = self._analyze_with_regex(content)
               
            if not analysis_result:
                return
               
            sources = analysis_result.get("sources", [])
            sinks = analysis_result.get("sinks", [])
           
            db = SessionLocal()
            try:
                js_file = db.query(JsFile).filter(JsFile.id == uuid.UUID(file_id)).first()
                if js_file:
                    js_file.sources = {"items": sources, "count": len(sources)}
                    js_file.sinks = {"items": sinks, "count": len(sinks)}
                    db.commit()
                   
                vulnerabilities = self._detect_vulnerabilities(sources, sinks)
                vulnerabilities = self._detect_vulnerabilities(sources, sinks)
                self._save_findings(db, url, sources, sinks, vulnerabilities) # 👈 Save to DB
                await self._update_parameter_sinks(db, sources, sinks)
            
            finally:
                db.close()
        
        except Exception as e:
            logger.error(f"Error analyzing JS file {url}: {e}")
    async def _analyze_with_ast(self, content: str) -> Optional[Dict[str, Any]]:
        """Run the Node.js AST analysis script"""
        try:
            if not self.node_available:
                return None
            if not os.path.exists(self.ast_script_path):
                logger.error(f"AST script missing at {self.ast_script_path}")
                return None
 
            def run_sync():
                return subprocess.run(
                    ["node", self.ast_script_path],
                    input=content.encode('utf-8'),
                    capture_output=True,
                    timeout=30
                )
 
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, run_sync)
           
            if result.returncode != 0:
                return None
               
            output = result.stdout.decode('utf-8', errors='ignore').strip()
            if not output:
                return None
                 
            return json.loads(output)
           
        except Exception as e:
            logger.error(f"AST analysis failed: {e}")
            return None
 
    def _analyze_with_regex(self, content: str) -> Dict[str, Any]:
        """Fallback regex-based analysis"""
        sources = []
        sinks = []
       
        source_patterns = ["location.search", "location.hash", "document.cookie", "URLSearchParams"]
        sink_patterns = ["innerHTML", "eval\\(", "setTimeout\\(", "location.assign"]
       
        lines = content.split('\n')
        for i, line in enumerate(lines, 1):
            for pat in source_patterns:
                if pat in line:
                    sources.append({"name": pat, "line": i, "type": "heuristic"})
            for pat in sink_patterns:
                import re
                if re.search(pat, line):
                    sinks.append({"name": pat.replace("\\(", ""), "line": i, "type": "heuristic", "risk": "unknown"})
                   
        return {"sources": sources, "sinks": sinks}
 
    def _detect_vulnerabilities(self, sources: List[Dict], sinks: List[Dict]) -> List[Dict]:
        """Correlate sources and sinks"""
        vulns = []
        if not sources or not sinks:
            return []
           
        for sink in sinks:
            if sink.get("risk") in ["high", "critical"]:
                vulns.append({
                    "type": sink.get("type", "UNKNOWN"),
                    "sink": sink,
                    "sources_present": [s["name"] for s in sources],
                    "confidence": "medium"
                })
        return vulns
   
    def _save_findings(self, db: Session, url: str, sources: List[Dict], sinks: List[Dict], vulnerabilities: List[Dict]):
        """Save structured findings to AuditLog (and logs)"""
        import hashlib
        from database.models import AuditLog # Ensure import available
       
        findings_details = []
        for vuln in vulnerabilities:
             finding = {
                "type": "Potential_DOM_XSS",
                "source": ", ".join(vuln.get("sources_present", [])),
                "source_line": 0,
                "sink": vuln.get("sink", {}).get("name", ""),
                "sink_line": vuln.get("sink", {}).get("line", 0),
                "severity": "High" if vuln.get("sink", {}).get("risk") == "high" else "Medium",
                "confidence": 0.8,
                "analysis_method": "ast",
                "explanation": f"Potential flow from {vuln.get('sources_present')} to {vuln.get('sink', {}).get('name')}"
            }
             findings_details.append(finding)
        
             # Persist finding
             db.add(AuditLog(
                 scan_id=uuid.UUID(self.scan_id),
                 agent="js_analyzer",
                 action="vulnerability_found",
                 details={"url": url, "finding": finding}
             ))
        
        db.commit()

        output = {
            "url": url,
            "hash": hashlib.sha256(url.encode()).hexdigest()[:16],
            "sources_detected": [{"type": s.get("name", "unknown"), "line": s.get("line", 0), "confidence": 1.0} for s in sources],
            "sinks_detected": [{"type": s.get("name", ""), "line": s.get("line", 0), "confidence": 1.0} for s in sinks],
            "findings": findings_details
        }
        logger.info(json.dumps(output))
   
    async def _update_parameter_sinks(self, db: Session, sources: List[Dict], sinks: List[Dict]):
        """Update parameter correlations"""
        try:
            stmt_params = select(Parameter).where(Parameter.scan_id == uuid.UUID(self.scan_id))
            parameters = db.execute(stmt_params).scalars().all()
           
            if not parameters:
                return
               
            has_source_access = any(
                s["name"] in ["location.search", "URLSearchParams", "location.hash"]
                for s in sources
            )
           
            if has_source_access:
                param_related_sinks = [
                    sink["name"] for sink in sinks
                    if sink.get("risk") in ["high", "critical"]
                ]
               
                for param in parameters:
                    if param_related_sinks and hasattr(param, 'js_sink_usage'):
                        existing = getattr(param, 'js_sink_usage', None) or ""
                        new_sinks = set(existing.split(",")) if existing else set()
                        new_sinks.update(param_related_sinks)
                        new_sinks.discard("")
                        param.js_sink_usage = ",".join(new_sinks)
                           
            db.commit()
           
        except Exception as e:
            logger.error(f"Failed to update parameter sinks: {e}")
 