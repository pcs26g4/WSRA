# WSRA/agents/mapper.py

import uuid
from datetime import datetime
from typing import Dict, Any, List, Set

from bs4 import BeautifulSoup
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

from database.connection import SessionLocal
from database.models import HtmlPage, Sitemap


class MapperAgent:
    """
    DETERMINISTIC MAPPER AGENT

    ✔ Selector-safe
    ✔ No duplicates
    ✔ Sitemap v2 only
    """
    def __init__(self, llm_enabled: bool = False):
        from llm.gemini_client import LLMClient
        from config.settings import settings
        self.llm_enabled = llm_enabled
        self.llm = LLMClient(
            enabled=llm_enabled,
            agent_name="MapperAgent",
            model_name=settings.LLM_MODEL_MAPPER
        )

    async def generate_sitemap_from_scan(self, scan_id: uuid.UUID) -> str:
        db: Session = SessionLocal()
        
        try:
            # 1️⃣ Check for existing sitemap
            existing_sitemap = db.query(Sitemap).filter(
                Sitemap.scan_id == scan_id
            ).first()

            sitemap_data = {}
            processed_urls = set()

            if existing_sitemap and existing_sitemap.sitemap_data:
                sitemap_data = dict(existing_sitemap.sitemap_data)
                # Load existing pages to avoid reprocessing
                if "pages" in sitemap_data:
                     processed_urls = set(sitemap_data["pages"].keys())

            # 2️⃣ Fetch ONLY new pages
            pages = db.query(HtmlPage).filter(
                HtmlPage.scan_id == str(scan_id)
            ).all()

            pages_data: Dict[str, Any] = sitemap_data.get("pages", {})
            
            updates = 0
            for page in pages:
                if page.url in processed_urls:
                    continue

                wsra_analysis = self._extract_dom(page.html)
                interactions = self._build_interactions(
                    page_url=page.url,
                    analysis=wsra_analysis,
                )

                pages_data[page.url] = {
                    "wsra_analysis": wsra_analysis,
                    "interactions": interactions,
                }
                updates += 1

                # Save Interaction Targets to DB for Orchestrator
                from database.models import InteractionTarget
                
                for interaction in interactions:
                    # Check duplicate
                    exists = db.query(InteractionTarget).filter(
                        InteractionTarget.scan_id == scan_id,
                        InteractionTarget.source_url == page.url,
                        InteractionTarget.element_selector == interaction["selector"]
                    ).first()
                    
                    if not exists:
                        db.add(InteractionTarget(
                            scan_id=scan_id,
                            source_url=page.url,
                            element_type=interaction["type"],
                            element_selector=interaction["selector"],
                            attributes_json=interaction
                        ))
                
                updates += 1

            if updates == 0 and existing_sitemap:
                return str(existing_sitemap.id)

            sitemap_data["pages"] = pages_data
            if not sitemap_data.get("target") and pages:
                 sitemap_data["target"] = pages[0].url

            if existing_sitemap:
                # Update in place
                flag_modified(existing_sitemap, "sitemap_data")
                existing_sitemap.updated_at = datetime.utcnow()
                db.commit()
                return str(existing_sitemap.id)
            else:
                sitemap_id = uuid.uuid4()
                final_data = {
                    "version": 2,
                    "scan_id": str(scan_id),
                    "created_at": datetime.utcnow().isoformat(),
                    "target": sitemap_data.get("target"),
                    "pages": pages_data,
                }
                db.add(Sitemap(
                    id=sitemap_id,
                    scan_id=scan_id,
                    sitemap_data=final_data,
                ))
                db.commit()
                return str(sitemap_id)

        finally:
            db.close()

    # ======================================================
    # DOM EXTRACTION
    # ======================================================

    def _extract_dom(self, html: str) -> Dict[str, Any]:
        soup = BeautifulSoup(html, "html.parser")

        links = []
        for a in soup.find_all("a", href=True):
            selector = (
                f"#{a['id']}" if a.get("id")
                else f"a[href='{a['href']}']"
            )

            links.append({
                "href_value": a.get("href"),
                "link_text": a.get_text(strip=True),
                "css_selector": selector,
            })

        buttons = self._extract_buttons(soup)

        forms = []
        for form in soup.find_all("form"):
            action = form.get("action")
            if not action:
                continue

            forms.append({
                "action": action,
                "method": (form.get("method") or "GET").upper(),
            })

        return {
            "links": links,
            "forms": forms,
            "functional_buttons": buttons,
        }

    # ======================================================
    # BUTTON EXTRACTION (🔥 FIXED)
    # ======================================================

    def _extract_buttons(self, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        buttons = []
        seen: Set[str] = set()

        for btn in soup.find_all("button"):
            selector = self._build_button_selector(btn)
            if not selector or selector in seen:
                continue

            seen.add(selector)

            buttons.append({
                "button_text": btn.get_text(strip=True),
                "css_selector": selector,
            })

        return buttons

    def _build_button_selector(self, btn) -> str | None:
        # 1️⃣ ID
        if btn.get("id"):
            return f"#{btn['id']}"

        # 2️⃣ data-* attributes
        for attr, val in btn.attrs.items():
            if attr.startswith("data-") and val:
                return f"button[{attr}='{val}']"

        # 3️⃣ aria-label
        if btn.get("aria-label"):
            return f"button[aria-label='{btn['aria-label']}']"

        # 4️⃣ visible text
        text = btn.get_text(strip=True)
        if text and len(text) <= 40:
            return f"button:has-text('{text}')"

        # ❌ reject unsafe selector
        return None

    # ======================================================
    # INTERACTION GENERATION
    # ======================================================

    def _build_interactions(
        self,
        *,
        page_url: str,
        analysis: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        interactions: List[Dict[str, Any]] = []

        for link in analysis.get("links", []):
            interactions.append({
                "id": str(uuid.uuid4()),
                "type": "navigate",
                "method": "click",
                "selector": link["css_selector"],
                "source_url": page_url,
                "destination": link["href_value"],
                "confidence": 0.9,
            })

        for form in analysis.get("forms", []):
            interactions.append({
                "id": str(uuid.uuid4()),
                "type": "form",
                "method": "submit",
                "selector": f"form[action='{form['action']}']",
                "source_url": page_url,
                "destination": form["action"],
                "confidence": 0.85,
            })

        for btn in analysis.get("functional_buttons", []):
            interactions.append({
                "id": str(uuid.uuid4()),
                "type": "button",
                "method": "click",
                "selector": btn["css_selector"],
                "source_url": page_url,
                "destination": None,
                "confidence": 0.75,
            })

        return interactions
