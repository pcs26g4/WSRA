
import json
import csv
import uuid
import os
from typing import Dict, Any, List
from datetime import datetime
from database.connection import SessionLocal
from database.models import Scan, HtmlPage, Parameter, JsFile, AuditLog, Sitemap

class ReportGeneratorAgent:
    """
    Generates scan reports in multiple formats:
    1. JSON Sitemap (Machine-Readable)
    2. CSV Parameter Inventory (Burp Suite Compatible)
    3. Markdown Report (Human-Readable)
    """

    def generate_reports(self, scan_id: str):
        """
        Generates all reports and saves them ONLY to the database.
        """
        import io
        from database.models import Export
            
        db = SessionLocal()
        try:
            scan = db.query(Scan).filter(Scan.id == uuid.UUID(scan_id)).first()
            if not scan:
                raise ValueError(f"Scan {scan_id} not found")

            # Helper for DB persistence
            def _persist_export(fmt: str, content: str):
                existing = db.query(Export).filter_by(scan_id=uuid.UUID(scan_id), format=fmt).first()
                if existing:
                    existing.content = content
                else:
                    db.add(Export(scan_id=uuid.UUID(scan_id), format=fmt, content=content))
                db.commit()

            # Statistics (Sync with Summary Dashboard)
            from database.models import Url, NetworkRequest
            
            urls = db.query(Url).filter(Url.scan_id == uuid.UUID(scan_id)).all()
            network_requests = db.query(NetworkRequest).filter(NetworkRequest.scan_id == uuid.UUID(scan_id)).all()
            total_params = db.query(Parameter).filter(Parameter.scan_id == uuid.UUID(scan_id)).count()
            total_js = db.query(JsFile).filter(JsFile.scan_id == uuid.UUID(scan_id)).count()
            
            # Smart Endpoint Discovery Logic (Deduplicated & Cleaned)
            STATIC_EXTENSIONS = {
                '.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico', 
                '.css', '.woff', '.woff2', '.ttf', '.eot', '.map', 
                '.js', '.json', '.xml', '.txt'
            }
            
            def is_relevant_endpoint(url_str):
                try:
                    from urllib.parse import urlparse
                    parsed = urlparse(url_str)
                    path = parsed.path.lower()
                    
                    # 1. Filter Extensions (No JS/CSS/Images/etc)
                    if any(path.endswith(ext) for ext in STATIC_EXTENSIONS):
                        return False
                    
                    # 2. Filter External Domains
                    # scan.target_domain might be "https://example.com" or just "example.com"
                    target_host = scan.target_domain.replace("https://", "").replace("http://", "").split("/")[0]
                    if target_host not in parsed.netloc:
                        return False
                        
                    return True
                except:
                    return False

            def canonicalize(u):
                # 1. Remove fragment
                u = u.split('#')[0]
                # 2. Strip trailing slash to fix duplicates like target.com vs target.com/
                if u.endswith('/'):
                    u = u[:-1]
                return u

            seen_endpoints = set()
            endpoints_list = []
            
            # Combine Network Traffic and Crawl Data
            for req in network_requests:
                clean_url = canonicalize(req.url)
                key = f"{req.method or 'GET'}:{clean_url}"
                if key not in seen_endpoints and is_relevant_endpoint(clean_url):
                    seen_endpoints.add(key)
                    endpoints_list.append(clean_url)

            for u in urls:
                clean_url = canonicalize(u.url)
                key = f"GET:{clean_url}"
                if key not in seen_endpoints and is_relevant_endpoint(clean_url):
                    seen_endpoints.add(key)
                    endpoints_list.append(clean_url)

            stats = {
                "total_urls": len(urls),
                "total_parameters": total_params,
                "total_js_files": total_js,
                "total_endpoints": len(endpoints_list)
            }

            findings = db.query(AuditLog).filter(
                AuditLog.scan_id == uuid.UUID(scan_id),
                AuditLog.action.in_({"missing_csrf", "vulnerability_found"})
            ).all()

            # ----------------------------------------------------
            # 1. JSON Report
            # ----------------------------------------------------
            
            # Fetch Vulnerability Hints
            from database.models import VulnerabilityHint
            vuln_hints = db.query(VulnerabilityHint).filter(
                VulnerabilityHint.scan_id == uuid.UUID(scan_id)
            ).all()

            json_report = {
                "scan_id": scan_id,
                "target": scan.target_domain,
                "scan_date": scan.started_at.isoformat() if scan.started_at else datetime.utcnow().isoformat(),
                "statistics": stats,
                "features": [{"name": "Discovered Endpoints", "urls": endpoints_list}],
                "findings": [f.details for f in findings],
                "vulnerability_hints": [
                    {
                        "type": h.type,
                        "parameter": h.parameter,
                        "endpoint": h.endpoint,
                        "location": h.location,
                        "confidence": h.confidence,
                        "evidence": h.evidence,
                        "manual_test": h.manual_test
                    } for h in vuln_hints
                ]
            }
            json_content = json.dumps(json_report, indent=2)
            _persist_export("json", json_content)

            # ----------------------------------------------------
            # 2. CSV Parameter Inventory
            # ----------------------------------------------------
            params = db.query(Parameter).filter(Parameter.scan_id == scan_id).all()
            csv_output = io.StringIO()
            writer = csv.writer(csv_output)
            writer.writerow(["URL", "Parameter", "Type", "Confidence"])
            seen_params = set()
            for p in params:
                url = p.endpoints[0] if p.endpoints and isinstance(p.endpoints, list) and len(p.endpoints) > 0 else (str(p.endpoints) if p.endpoints else "")
                key = (url, p.name, p.location)
                if key not in seen_params:
                    seen_params.add(key)
                    writer.writerow([url, p.name, p.location, "High"])
            
            csv_content = csv_output.getvalue()
            _persist_export("csv", csv_content)

            # ----------------------------------------------------
            # 3. Markdown Report
            # ----------------------------------------------------
            md_output = io.StringIO()
            md_output.write(f"# Security Reconnaissance Report\n\n")
            md_output.write(f"**Target:** {scan.target_domain}\n")
            md_output.write(f"**Scan Date:** {scan.started_at}\n\n")
            md_output.write("## Summary\n")
            md_output.write(f"- **URLs Discovered:** {stats['total_urls']}\n")
            md_output.write(f"- **Parameters Found:** {stats['total_parameters']}\n")
            md_output.write(f"- **JavaScript Files:** {stats['total_js_files']}\n")
            md_output.write(f"- **API Endpoints:** {stats['total_endpoints']}\n")
            md_output.write(f"- **Vulnerability Hints:** {len(vuln_hints)}\n\n")
            
            md_output.write("## High-Priority Findings\n")
            if not findings and not vuln_hints:
                md_output.write("No high-priority findings detected.\n")
            
            # Existing specific findings
            for idx, finding in enumerate(findings, 1):
                details = finding.details or {}
                name = finding.action.replace("_", " ").title()
                url = details.get("url", "unknown")
                md_output.write(f"### {idx}. {name}\n")
                md_output.write(f"- **Endpoint:** {url}\n")
                if finding.action == "missing_csrf":
                    md_output.write(f"- **Risk:** Medium\n")
                    md_output.write(f"- **Evidence:** Form missing anti-CSRF tokens.\n")
                else:
                    md_output.write(f"- **Details:** {json.dumps(details)}\n")
                md_output.write("\n")

            # Vulnerability Hints Section
            if vuln_hints:
                md_output.write("## Vulnerability Hints\n")
                md_output.write("> These are high-signal areas for manual testing.\n\n")
                
                for idx, hint in enumerate(vuln_hints, 1):
                    md_output.write(f"### {idx}. {hint.type} Hint: `{hint.parameter}`\n")
                    md_output.write(f"- **Endpoint:** `{hint.endpoint or 'N/A'}`\n")
                    
                    try:
                         # Evidence Formatting
                         evidence_str = ""
                         if hint.evidence:
                            if isinstance(hint.evidence, dict):
                                for k,v in hint.evidence.items():
                                    evidence_str += f"\n  - {k}: {v}"
                            else:
                                evidence_str = str(hint.evidence)
                    except: evidence_str = "Unavailable"

                    md_output.write(f"- **Evidence:**{evidence_str}\n")
                    md_output.write(f"- **Manual Test:** `{hint.manual_test}`\n")
                    md_output.write("\n")

            md_content = md_output.getvalue()
            _persist_export("markdown", md_content)

            return True

        finally:
            db.close()
