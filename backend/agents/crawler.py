import asyncio
import hashlib
import logging
import re
from datetime import datetime, timezone
from urllib.parse import urlparse, urljoin, parse_qs

import requests
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeoutError
from sqlalchemy.orm import Session

from database.models import (
    Scan,
    Url,
    HtmlPage,
    JsFile,
    NetworkRequest,
    Form,
    Parameter,
    PageSnapshot,
    AuditLog,
    ScanStatistics,
)
from config.settings import settings

logger = logging.getLogger("crawl_agent")

# ======================================================
# UTILS
# ======================================================

def clean_text(html: str) -> str:
    soup = BeautifulSoup(html or "", "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    return re.sub(r"\s+", " ", soup.get_text()).strip()


def sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


# ======================================================
# PLAYWRIGHT CRAWL
# ======================================================

async def _playwright_crawl(url: str, cookies: list = None, existing_context=None) -> dict:
    p = None
    browser = None
    context = None
    
    try:
        if existing_context:
            context = existing_context
            if cookies:
                try:
                    await context.add_cookies(cookies)
                except Exception:
                    pass
        else:
            p = await async_playwright().start()
            browser = await p.chromium.launch(
                headless=settings.HEADLESS,
                slow_mo=settings.BROWSER_SLOW_MO
            )
            context = await browser.new_context()
            if cookies:
                try:
                    await context.add_cookies(cookies)
                    logger.info(f"🍪 Restored {len(cookies)} session cookies")
                except Exception as e:
                    logger.warning(f"Failed to restore cookies: {e}")

        try:
            page = await context.new_page()
            
            network_events = []

            async def on_response(resp):
                try:
                    req = resp.request
                    ct = resp.headers.get("content-type", "")
                    body = await resp.text() if "text" in ct or "json" in ct else None

                    network_events.append({
                        "url": req.url,
                        "method": req.method,
                        "status": resp.status,
                        "headers": dict(resp.headers),
                        "resource_type": req.resource_type,
                        "body": body,
                    })
                except Exception as e:
                    logger.debug(f"Failed to parse response for {resp.url}: {e}")

            page.on("response", on_response)

            try:
                # 🔥 IMPROVED WAIT STRATEGY
                # 1. Wait for "load" event (resources loaded)
                await page.goto(url, timeout=settings.CRAWL_TIMEOUT_MS, wait_until="load")
                
                try:
                    # 2. Wait for network to settle (SPA support)
                    await page.wait_for_load_state("networkidle", timeout=20000) 
                except Exception:
                    pass # Continue if network never strictly idles

                # 3. Explicit grace period for final JS rendering
                await page.wait_for_timeout(3000)

                return {
                    "success": True,
                    "html": await page.content(),
                    "final_url": page.url,
                    "network": network_events,
                }

            except PlaywrightTimeoutError:
                return {
                    "success": True,
                    "html": await page.content(),
                    "final_url": page.url,
                    "network": network_events,
                    "partial": True,
                }
            except Exception as e:
                logger.error(f"Crawl error for {url}: {e}")
                return {
                     "success": False,
                     "error": str(e),
                     "final_url": url,
                     "network": network_events
                }
            finally:
                if page and not page.is_closed():
                    await page.close()

        except Exception as e:
             logger.error(f"Context/Page error: {e}")
             return {"success": False, "error": str(e)}

    finally:
        # Only close browser if we created it
        if not existing_context:
            if context:
                await context.close()
            if browser:
                await browser.close()
            if p:
                await p.stop()


# ======================================================
# MAIN CRAWLER
# ======================================================

async def run_crawler(*, url: str, db: Session, scan_id: str, source: str = "orchestrator", cookies: list = None, context=None): # 👈 Added context
    logger.info(f"🕷️ Crawling: {url}")

    scan = db.query(Scan).filter(Scan.id == scan_id).first()
    if not scan:
        scan = Scan(
            id=scan_id,
            target_domain=urlparse(url).netloc,
            status="RUNNING",
            started_at=datetime.now(timezone.utc),
        )
        db.add(scan)
        db.commit()

    db.add(AuditLog(
        scan_id=scan.id,
        agent="crawler",
        action="crawl_started",
        details={"url": url, "source": source},
    ))
    db.commit()

    if not db.query(Url).filter_by(scan_id=scan.id, url=url).first():
        db.add(Url(scan_id=scan.id, url=url, depth_level=0, status_code=0))
        db.commit()

    result = await _playwright_crawl(url, cookies=cookies, existing_context=context) # 👈 Pass context

    html = result.get("html", "")
    final_url = result.get("final_url", url)
    network = result.get("network", [])

    text = clean_text(html)
    fingerprint = sha256(text)

    html_page = HtmlPage(
        scan_id=scan.id,
        url=final_url,
        hash=fingerprint,
        html=html,
    )
    db.add(html_page)
    db.flush()

    db.add(PageSnapshot(
        scan_id=scan.id,
        url=final_url,
        fingerprint=fingerprint,
        html=html,
        text=text,
    ))

    soup = BeautifulSoup(html, "html.parser")

    # ================= JS FILES =================

    # External JS
    for script in soup.find_all("script", src=True):
        js_url = urljoin(final_url, script["src"])
        if db.query(JsFile).filter_by(scan_id=scan.id, url=js_url).first():
            continue
        try:
            loop = asyncio.get_running_loop()
            def fetch_js():
                # 🔥 FIX: Use cookies for JS fetch
                session_cookies = {}
                if cookies:
                    for c in cookies:
                        session_cookies[c['name']] = c['value']
                return requests.get(js_url, timeout=settings.JS_FETCH_TIMEOUT_SECONDS, verify=False, cookies=session_cookies)
            
            r = await loop.run_in_executor(None, fetch_js) # 👈 Non-blocking
            content = r.text if r.status_code == 200 and r.text else ""
        except Exception as e:
            logger.debug(f"Failed to fetch JS {js_url}: {e}")
            content = ""

        db.add(JsFile(scan_id=scan.id, url=js_url, content=content))

    # Inline JS (🔥 FIX)
    for script in soup.find_all("script"):
        if script.string and script.string.strip():
            content = script.string.strip()
            fid = sha256(content)[:8]
            inline_url = f"{final_url}#inline-{fid}"

            if not db.query(JsFile).filter_by(scan_id=scan.id, url=inline_url).first():
                db.add(JsFile(scan_id=scan.id, url=inline_url, content=content))

    # ================= NETWORK =================

    for ev in network:
        # Check uniqueness (scan_id + url + method)
        # We might have same request multiple times if page loads same resource? 
        # But for 'recon', storing unique request types is enough.
        exists = db.query(NetworkRequest).filter(
            NetworkRequest.scan_id == scan.id,
            NetworkRequest.url == ev["url"],
            NetworkRequest.method == ev["method"]
        ).first()

        if exists:
            continue

        db.add(NetworkRequest(
            scan_id=scan.id,
            url=ev["url"],
            method=ev["method"],
            response_status=ev["status"],
            response_body=ev["body"],
            parameters={
                "headers": ev["headers"],
                "resource_type": ev["resource_type"],
            },
        ))

    # ================= FORMS =================
    
    for form in soup.find_all("form"):
        form_action = form.get("action", "")
        form_method = form.get("method", "GET").upper()
        
        # Deduplication check
        existing_form = db.query(Form).filter(
            Form.scan_id == scan.id,
            Form.url == final_url,
            Form.action == form_action,
            Form.method == form_method
        ).first()
        
        if existing_form:
            continue
            
        db.add(Form(
            scan_id=scan.id,
            url=final_url,
            method=form_method,
            action=form_action,
            fields=[
                {"name": i.get("name"), "type": i.get("type")}
                for i in form.find_all("input")
            ],
        ))

    # ================= PARAMETERS =================

    seen = set()
    for ev in network:
        parsed = urlparse(ev["url"])
        for name in parse_qs(parsed.query):
            if (name, "query") in seen:
                continue
            seen.add((name, "query"))

            db.add(Parameter(
                scan_id=scan.id,
                name=name,
                location="query",
                endpoints=[ev["url"]],
                reflected_in_response=False,
            ))

    db.add(AuditLog(
        scan_id=scan.id,
        agent="crawler",
        action="crawl_completed",
        details={"url": final_url, "message": f"Successfully crawled and analyzed {final_url}"},
    ))

    _update_stats(db, scan.id)
    db.commit()

    logger.info(f"✅ Crawl completed: {final_url}")

    return {"status": "success", "final_url": final_url, "html": html}


def _update_stats(db: Session, scan_id: str):
    db.merge(ScanStatistics(
        scan_id=scan_id,
        total_urls=db.query(Url).filter_by(scan_id=scan_id).count(),
        total_js_files=db.query(JsFile).filter_by(scan_id=scan_id).count(),
        total_parameters=db.query(Parameter).filter_by(scan_id=scan_id).count(),
        total_network_requests=db.query(NetworkRequest).filter_by(scan_id=scan_id).count(),
        updated_at=datetime.now(timezone.utc),
    ))
