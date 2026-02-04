import logging
import uuid
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select

from database.models import Scan, Parameter, JsFile, NetworkRequest, VulnerabilityHint
# from config.settings import settings # If needed later

logger = logging.getLogger("vuln_hinter")

class VulnHinterAgent:
    """
    Vulnerability Hinter Agent
    Generates hypothesis-based signals for manual testing.
    Does NOT exploit or fuzz.
    """

    def __init__(self, scan_id: str, llm_enabled: bool = False):
        self.scan_id = scan_id
        # LLM not currently used, but kept for signature compatibility with orchestrator
        self.llm_enabled = llm_enabled 

    async def run(self, db: Session):
        """Run the analysis logic"""
        logger.info(f"Starting Vulnerability Hinter for scan {self.scan_id}")
        
        # Fetch data
        scan_uuid = uuid.UUID(self.scan_id)
        params = db.query(Parameter).filter(Parameter.scan_id == scan_uuid).all()
        js_findings = db.query(JsFile).filter(JsFile.scan_id == scan_uuid).all()
        
        hints = []

        # 1. Reflected XSS Hint
        hints.extend(self._detect_reflected_xss(params, js_findings))
        
        # 2. DOM-Based XSS Hint
        hints.extend(self._detect_dom_xss(js_findings))

        # 3. SSRF Hint
        hints.extend(self._detect_ssrf(params))

        # 4. LFI / Path Traversal Hint
        hints.extend(self._detect_lfi(params))

        # 5. Open Redirect Hint
        hints.extend(self._detect_open_redirect(params))

        # Save hints
        self._save_hints(db, hints)
        logger.info(f"Generated {len(hints)} hints for scan {self.scan_id}")
        return hints

    def _detect_reflected_xss(self, params: List[Parameter], js_findings: List[JsFile]) -> List[Dict]:
        detected = []
        for param in params:
            if param.reflected_in_response:
                sink = self._find_sink_for_param(param.name, js_findings)
                
                confidence = 0.7
                evidence = {"reflected": True}
                
                if sink:
                    confidence = 0.9
                    evidence["js_sink"] = f"{sink.get('type')} at line {sink.get('line')}"

                if confidence >= 0.5:
                    detected.append({
                        "type": "Reflected XSS",
                        "parameter": param.name,
                        "location": param.location,
                        "confidence": confidence,
                        "evidence": evidence,
                        "manual_test": f"<script>alert('XSS-{param.name}')</script>"
                    })
        return detected

    def _detect_dom_xss(self, js_findings: List[JsFile]) -> List[Dict]:
        detected = []
        dangerous_sinks = ["innerHTML", "eval", "document.write", "setTimeout"]
        user_inputs = ["location.search", "location.hash", "URLSearchParams", "document.cookie"]

        for js in js_findings:
            if not js.sources or not js.sinks:
                continue

            sources = js.sources.get("items", []) if isinstance(js.sources, dict) else js.sources
            sinks = js.sinks.get("items", []) if isinstance(js.sinks, dict) else js.sinks
            
            has_input = any(s.get("name") in user_inputs for s in sources)
            if not has_input:
                continue

            for sink in sinks:
                sink_name = sink.get("name", "").replace("(", "").replace(")", "")
                if any(ds in sink_name for ds in dangerous_sinks):
                    detected.append({
                        "type": "DOM XSS",
                        "parameter": "N/A (DOM)",
                        "location": f"JS File: {js.url}",
                        "confidence": 0.8,
                        "evidence": {
                            "source": [s.get("name") for s in sources if s.get("name") in user_inputs],
                            "sink": sink_name,
                            "line": sink.get("line")
                        },
                        "manual_test": f"Control {sources[0].get('name')} to reach {sink_name}"
                    })
        return detected

    def _detect_ssrf(self, params: List[Parameter]) -> List[Dict]:
        detected = []
        suspect_names = ["url", "callback", "redirect", "uri", "link", "src", "dest"]
        
        for param in params:
            if any(s in param.name.lower() for s in suspect_names):
                detected.append({
                    "type": "SSRF",
                    "parameter": param.name,
                    "location": param.location,
                    "confidence": 0.6,
                    "evidence": {"sensitive_param_name": param.name},
                    "manual_test": f"http://localhost:80 or http://169.254.169.254"
                })
        return detected

    def _detect_lfi(self, params: List[Parameter]) -> List[Dict]:
        detected = []
        suspect_names = ["file", "path", "template", "view", "doc"]
        
        for param in params:
            if any(s in param.name.lower() for s in suspect_names):
                 detected.append({
                    "type": "LFI / Path Traversal",
                    "parameter": param.name,
                    "location": param.location,
                    "confidence": 0.6,
                    "evidence": {"sensitive_param_name": param.name},
                    "manual_test": "../../../etc/passwd"
                })
        return detected

    def _detect_open_redirect(self, params: List[Parameter]) -> List[Dict]:
        detected = []
        suspect_names = ["next", "return", "redirect", "forward", "out"]
        
        for param in params:
            if any(s in param.name.lower() for s in suspect_names):
                 detected.append({
                    "type": "Open Redirect",
                    "parameter": param.name,
                    "location": param.location,
                    "confidence": 0.6,
                    "evidence": {"sensitive_param_name": param.name},
                    "manual_test": "https://evil.com"
                })
        return detected

    def _find_sink_for_param(self, param_name: str, js_findings: List[JsFile]) -> Optional[Dict]:
        for js in js_findings:
             if js.sources and isinstance(js.sources, dict):
                 items = js.sources.get("items", [])
                 for item in items:
                     if param_name in item.get("name", ""):
                         sinks = js.sinks.get("items", []) if isinstance(js.sinks, dict) else js.sinks
                         if sinks:
                             return sinks[0]
        return None

    def _save_hints(self, db: Session, hints: List[Dict]):
        if not hints:
            return

        db_hints = []
        for h in hints:
            db_hint = VulnerabilityHint(
                scan_id=uuid.UUID(self.scan_id),
                type=h["type"],
                parameter=h["parameter"],
                endpoint=h.get("endpoint", ""),
                location=h["location"],
                confidence=h["confidence"],
                evidence=h["evidence"],
                manual_test=h["manual_test"]
            )
            db_hints.append(db_hint)
        
        db.add_all(db_hints)
        db.commit()
