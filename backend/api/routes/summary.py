from fastapi import APIRouter, HTTPException
from database.connection import SessionLocal
from database.models import (
    Scan, Url, JsFile, Form, Parameter, NetworkRequest,
    InteractionOutcome, AuditLog, LLMRequest, VulnerabilityHint
)
import uuid
from typing import Dict, Any, List
from datetime import datetime

router = APIRouter(prefix="/scan", tags=["Summary"])

# Helper function to extract vulnerabilities (Combined logic: LLM + AuditLog)
def _extract_vulnerabilities(llm_requests, audit_logs):
    vulnerabilities = []
    
    # 1. Extract from LLM Requests (AI Findings)
    # (Currently no AI vuln hunters active, but keeping structure for future)
    pass

    # 2. Extract from Audit Logs (Deterministic Findings)
    FINDING_ACTIONS = {"missing_csrf"}
    SEVERITY_MAP = {"missing_csrf": "medium"}
    
    for log in audit_logs:
        if log.action in FINDING_ACTIONS:
            details = log.details or {}
            url = details.get("url", "unknown")
            vulnerabilities.append({
                "id": str(log.id),
                "type": log.action,
                "severity": SEVERITY_MAP.get(log.action, "info"),
                "location": url,
                "description": details.get("description", f"Detected {log.action} at {url}"),
                "payload": "N/A"
            })

    return vulnerabilities

def _extract_endpoints(network_requests: List[Any], urls: List[Any], target_domain: str = "") -> List[Dict[str, Any]]:
    """
    Extracts unique application endpoints from network traffic and crawl data.
    Filters out static assets to focus on the application's functional attack surface.
    """
    endpoints = []
    seen = set()
    
    # Common static extensions to ignore in 'Endpoints' count
    STATIC_EXTENSIONS = {
        '.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico', 
        '.css', '.woff', '.woff2', '.ttf', '.eot', '.map',
        '.js', '.json', '.xml', '.txt'
    }

    target_host = ""
    if target_domain:
        target_host = target_domain.replace("https://", "").replace("http://", "").split("/")[0]

    def is_relevant(url):
        from urllib.parse import urlparse
        try:
            parsed = urlparse(url)
            path = parsed.path.lower()
            
            # Extension Filter
            if any(path.endswith(ext) for ext in STATIC_EXTENSIONS):
                return False
            
            # Domain Filter
            if target_host and target_host not in parsed.netloc:
                return False
                
            return True
        except:
             return False

    def canonicalize(u):
        u = u.split('#')[0]
        if u.endswith('/'):
            u = u[:-1]
        return u

    # 1. Process Network Requests (Discovery of API endpoints etc)
    for req in network_requests:
        # Deduplicate by Method + URL (ignoring fragment)
        clean_url = canonicalize(req.url)
        key = f"{req.method or 'GET'}:{clean_url}"
        
        if key not in seen and is_relevant(clean_url):
            seen.add(key)
            endpoints.append({
                "url": clean_url,
                "method": req.method or "GET",
                "status_code": req.response_status or 200
            })

    # 2. Process Crawled URLs (Ensuring all crawled pages are counted)
    for url_obj in urls:
        clean_url = canonicalize(url_obj.url)
        key = f"GET:{clean_url}"
        
        if key not in seen and is_relevant(clean_url):
            seen.add(key)
            endpoints.append({
                "url": clean_url,
                "method": "GET",
                "status_code": url_obj.status_code or 200
            })
            
    return endpoints

def _extract_features(urls):
    features = []
    url_groups = {}
    for url_obj in urls:
        url = url_obj.url
        feature_name = "General Website" 
        if '/user' in url or '/profile' in url: feature_name = "User Management"
        elif '/admin' in url: feature_name = "Administration"
        elif '/api' in url: feature_name = "API"
        elif '/auth' in url or '/login' in url: feature_name = "Authentication"
        elif '/cart' in url or '/checkout' in url: feature_name = "E-Commerce"
        elif '/blog' in url or '/post' in url: feature_name = "Content"
        
        if feature_name not in url_groups: url_groups[feature_name] = []
        url_groups[feature_name].append(url)
        
    for name, group in url_groups.items():
         features.append({"name": name, "count": len(group)})
    
    return features

def _generate_manual_tests(vulnerabilities, parameters):
    tests = []
    for vuln in vulnerabilities:
        vuln_type = vuln.get("type"); location = vuln.get("location", "Unknown")
        if vuln_type == "xss":
            tests.append({"type": "XSS Test", "endpoint": location, "payload": "<script>alert('XSS')</script>", "expected_result": "JS execution", "priority": "High"})
        elif vuln_type == "sql_injection":
            tests.append({"type": "SQL Injection Test", "endpoint": location, "payload": "' OR '1'='1", "expected_result": "SQL error / bypass", "priority": "Critical"})
        elif vuln_type == "missing_csrf":
             tests.append({"type": "CSRF Validation", "endpoint": location, "payload": "Submit form without token", "expected_result": "403 Forbidden", "priority": "Medium"})
    
    for p in parameters:
        if getattr(p, "reflected_in_response", False):
            tests.append({
                "type": "Reflected Parameter Test", "priority": "Medium",
                "endpoint": (p.endpoints or ["Unknown"])[0] if p.endpoints else "Unknown",
                "payload": f"{p.name}=<img src=x onerror=alert(1)>", "expected_result": "Reflection"
            })
    return tests

@router.get("/{scan_id}/summary")
async def scan_summary(scan_id: str):
    db = SessionLocal()
    try:
        try:
            scan_uuid = uuid.UUID(scan_id)
        except ValueError: raise HTTPException(400, "Invalid scan ID format")

        scan = db.query(Scan).filter(Scan.id == scan_uuid).first()
        if not scan: raise HTTPException(404, "Scan not found")
        
        # 🔥 CRITICAL: Sync with Export Output
        # Try to get the statistics from the generated JSON report first
        from database.models import Export
        export_json = db.query(Export).filter(Export.scan_id == scan_uuid, Export.format == "json").first()
        
        report_stats = None
        report_features = None
        if export_json:
            try:
                report_data = json.loads(export_json.content)
                report_stats = report_data.get("statistics")
                report_features = report_data.get("features")
            except: pass

        # Fetch raw data for current state (Fallback or for Running scans)
        urls = db.query(Url).filter(Url.scan_id == scan_uuid).all()
        network_requests = db.query(NetworkRequest).filter(NetworkRequest.scan_id == scan_uuid).all()
        js_files = db.query(JsFile).filter(JsFile.scan_id == scan_uuid).all()
        forms = db.query(Form).filter(Form.scan_id == scan_uuid).all()
        parameters = db.query(Parameter).filter(Parameter.scan_id == scan_uuid).all()
        llm_requests = db.query(LLMRequest).filter(LLMRequest.scan_id == scan_uuid).all()
        # Fetch audit logs for live activity feed
        audit_logs = db.query(AuditLog).filter(AuditLog.scan_id == scan_uuid).order_by(AuditLog.timestamp.desc()).limit(20).all()
        
        # 🔥 NEW: Fetch Vulnerability Hints
        vuln_hints = db.query(VulnerabilityHint).filter(VulnerabilityHint.scan_id == scan_uuid).all()

        # Process data
        vulnerabilities = _extract_vulnerabilities(llm_requests, audit_logs)
        
        # 🔥 NEW: Merge Hints into Vulnerabilities List for Frontend
        for h in vuln_hints:
            vulnerabilities.append({
                "id": str(h.id),
                "type": h.type,
                "severity": "high" if h.confidence >= 0.8 else "medium",
                "location": f"{h.endpoint or 'Unknown'} (Param: {h.parameter})",
                "description": f"Confidence: {h.confidence}\nEvidence: {h.evidence}",
                "payload": h.manual_test,
                "remediation": "Input validation and output encoding recommended."
            })
        
        # Prepare live logs for UI
        live_logs = [{
            "id": str(log.id),
            "timestamp": log.timestamp.isoformat() if log.timestamp else None,
            "agent": log.agent,
            "action": log.action,
            "message": (log.details or {}).get("message") or f"{log.agent} performed {log.action}"
        } for log in audit_logs]
        
        # Use reports stats if available, otherwise calculate
        if report_stats:
            stats = report_stats
        else:
            dashboard_endpoints = _extract_endpoints(network_requests, urls, target_domain=scan.target_domain)
            stats = { 
                "total_urls": len(urls),
                "total_js_files": len(js_files), 
                "total_forms": len(forms),
                "total_parameters": len(parameters), 
                "total_network_requests": len(network_requests),
                "total_endpoints": len(dashboard_endpoints) 
            }

        # Sync Endpoints List
        report_endpoints = None
        if report_features:
            for feat in report_features:
                if feat.get("name") == "Discovered Endpoints":
                    report_endpoints = [{"url": u, "method": "GET", "status_code": 200} for u in feat.get("urls", [])]

        endpoints = report_endpoints if report_endpoints else _extract_endpoints(network_requests, urls, target_domain=scan.target_domain)
        features = report_features if report_features else _extract_features(urls)
        manual_tests = _generate_manual_tests(vulnerabilities, parameters)
        
        duration = 0
        if scan.started_at and scan.completed_at:
            duration = (scan.completed_at - scan.started_at).total_seconds()

        return {
            "scan_id": scan_id, "target": scan.target_domain, "status": scan.status, "duration": duration,
            "statistics": stats,
            "vulnerabilities": vulnerabilities,
            "endpoints": endpoints,
            "features": features,
            "js_files": [{"url": js.url, "risk_level": "High" if len(js.sinks or []) > 5 else "Medium" if len(js.sinks or []) > 0 else "Low"} for js in js_files],
            "forms": [{"url": f.url, "field_count": len(f.fields or [])} for f in forms],
            "manual_testing": manual_tests,
            "logs": live_logs
        }
    finally:
        db.close()
