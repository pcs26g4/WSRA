from typing import Dict, List, Any, Optional
import logging
from sqlalchemy.orm import Session

from playwright.async_api import async_playwright, Page, Browser, BrowserContext

from database.connection import SessionLocal
from database.models import NetworkRequest, AuditLog, PageSnapshot


from config.settings import settings

logger = logging.getLogger("network_monitor")


class NetworkMonitor:
    """
    Network + Runtime Browser Agent (SPA-aware)
    OWNS the Playwright browser lifecycle
    """

    def __init__(self, scan_id: str):
        self.scan_id = scan_id

        self._playwright = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None

    # ======================================================
    # 🔥 PLAYWRIGHT CONTROL
    # ======================================================

    async def get_page(self) -> Page:
        """
        Lazily create browser, context and page.
        """
        if self._page:
            return self._page

        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(
            headless=settings.HEADLESS,
            slow_mo=settings.BROWSER_SLOW_MO,
        )
        self._context = await self._browser.new_context()
        self._page = await self._context.new_page()

        # 🔥 Handle popups/new tabs (auto-switch context)
        def handle_popup(popup):
            logger.info("New tab/popup detected. Switching context.")
            self._page = popup
        
        self._page.on("popup", handle_popup)
        
        return self._page

    async def load_session(self, session_data: Dict[str, Any]):
        """
        Load authenticated cookies into browser context.
        """
        if not session_data or "cookies" not in session_data:
            return

        page = await self.get_page()
        await page.context.add_cookies(session_data["cookies"])

    async def close(self):
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()

    # ======================================================
    # 📸 SNAPSHOT
    # ======================================================

    def save_snapshot(self, *, url: str, fingerprint: str, page: Page):
        db: Session = SessionLocal()
        try:
            db.add(PageSnapshot(
                scan_id=self.scan_id,
                url=url,
                fingerprint=fingerprint,
                html=None,
                text=None,
            ))
            db.commit()
        finally:
            db.close()

    # ======================================================
    # 🔍 PASSIVE NETWORK ANALYSIS (UNCHANGED)
    # ======================================================

    def analyze(self) -> List[Dict[str, Any]]:
        session: Session = SessionLocal()
        findings = []

        try:
            requests = (
                session.query(NetworkRequest)
                .filter(NetworkRequest.scan_id == self.scan_id)
                .all()
            )

            for req in requests:
                findings.extend(self._analyze_request(req))

            for f in findings:
                session.add(AuditLog(
                    scan_id=self.scan_id,
                    agent="network_monitor",
                    action=f["type"],
                    details=f,
                ))

            session.commit()
            return findings

        finally:
            session.close()

    def _analyze_request(self, req: NetworkRequest) -> List[Dict[str, Any]]:
        results = []

        if req.url and req.url.startswith("http://"):
            results.append({
                "type": "unencrypted_traffic",
                "severity": "medium",
                "url": req.url,
            })

        if req.method == "GET" and req.url and "?" in req.url:
            query = req.url.split("?")[1].lower()
            if any(k in query for k in ("password", "token", "secret", "apikey")):
                results.append({
                    "type": "sensitive_data_in_url",
                    "severity": "high",
                    "url": req.url,
                })

        return results
