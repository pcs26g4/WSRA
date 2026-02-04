# WSRA/agents/interaction_agent.py

import logging
from typing import Dict, List, Optional
from urllib.parse import urlparse, urljoin

from database.models import Sitemap

logger = logging.getLogger(__name__)


class InteractionAgent:
    """
    STATELESS INTERACTION AGENT (SITEMAP v2 AWARE)

    HARD RULES:
    - NO loops
    - NO DB writes
    - NO crawl decisions
    - Executes EXACTLY ONE action per call
    - Orchestrator owns control flow
    """

    def __init__(self, *, llm_enabled: bool):
        from llm.gemini_client import LLMClient
        from config.settings import settings
        self.llm_enabled = llm_enabled
        self.llm = LLMClient(
            enabled=llm_enabled,
            agent_name="InteractionAgent",
            model_name=settings.LLM_MODEL_INTERACTION
        )

    # ======================================================
    # TARGET EXTRACTION
    # ======================================================

    def extract_targets(self, sitemap: Sitemap) -> List[Dict]:
        """
        PRIMARY:
        - Sitemap v2 → pages[].interactions[]

        FALLBACK:
        - Legacy sitemap v1 → html_pages[].wsra_analysis
        """

        if not sitemap or not sitemap.sitemap_data:
            return []

        data = sitemap.sitemap_data
        base_url = data.get("target")
        targets: List[Dict] = []

        # --------------------------------------------------
        # ✅ SITEMAP v2 (AUTHORITATIVE)
        # --------------------------------------------------
        pages = data.get("pages")
        if pages:
            for page_url, page in pages.items():
                for interaction in page.get("interactions", []):
                    selector = interaction.get("selector")
                    if not selector:
                        continue

                    targets.append({
                        "type": interaction.get("type"),
                        "method": interaction.get("method"),
                        "selector": selector,
                        "source_url": interaction.get("source_url") or page_url,
                        "target_url": interaction.get("destination"),
                        "base_url": base_url or page_url,
                    })

            if targets:
                logger.info(
                    "[InteractionAgent] Loaded %d interactions (v2)",
                    len(targets),
                )
                return targets

        # --------------------------------------------------
        # 🔁 LEGACY FALLBACK (v1)
        # --------------------------------------------------
        legacy_pages = data.get("html_pages", {})
        for page_url, page in legacy_pages.items():
            analysis = page.get("wsra_analysis", {})

            # ---- LINKS ----
            for link in analysis.get("links", []):
                href = link.get("href_value")
                selector = link.get("css_selector")
                if not href or not selector:
                    continue

                targets.append({
                    "type": "link",
                    "method": "click",
                    "selector": selector,
                    "source_url": page_url,
                    "target_url": href,
                    "base_url": base_url or page_url,
                })

            # ---- BUTTONS ----
            for button in analysis.get("functional_buttons", []):
                selector = button.get("css_selector")
                if not selector:
                    continue

                targets.append({
                    "type": "button",
                    "method": "click",
                    "selector": selector,
                    "source_url": page_url,
                    "target_url": None,
                    "base_url": base_url or page_url,
                })

            # ---- FORMS ----
            for form in analysis.get("forms", []):
                action = form.get("action")
                if not action:
                    continue

                targets.append({
                    "type": "form",
                    "method": "submit",
                    "selector": f"form[action='{action}']",
                    "source_url": page_url,
                    "target_url": action,
                    "base_url": base_url or page_url,
                })

        logger.info(
            "[InteractionAgent] Loaded %d interactions (legacy)",
            len(targets),
        )
        return targets

    # ======================================================
    # SINGLE ACTION EXECUTION
    # ======================================================

    async def execute_action(self, target: Dict) -> Dict[str, Optional[str]]:
        """
        Executes EXACTLY ONE interaction.

        Returns:
        - status: success | form_detected | skipped
        - new_url: Optional[str]
        """

        action_type = target.get("type")
        target_url = target.get("target_url")
        base_url = target.get("base_url")

        # ---- FORM ----
        if action_type == "form":
            return {
                "status": "form_detected",
                "new_url": None,
            }

        # ---- NAVIGATION / BUTTON ----
        if action_type in ("navigate", "link", "button"):
            return {
                "status": "success",
                "new_url": self._normalize_url(target_url, base_url),
            }

        return {
            "status": "skipped",
            "new_url": None,
        }

    # ======================================================
    # DOMAIN CHECK (RELATIVE URL SAFE)
    # ======================================================

    def is_same_domain(
        self,
        base_url: str,
        target_url: Optional[str],
    ) -> bool:
        """
        RULES:
        - Relative URLs → ALWAYS in scope
        - Absolute URLs → must match domain
        """

        if not target_url:
            return True

        # ✅ Relative URLs are always safe
        if target_url.startswith(("/", "?")) or "://" not in target_url:
            return True

        try:
            return (
                urlparse(base_url).netloc
                == urlparse(target_url).netloc
            )
        except Exception:
            return False

    # ======================================================
    # URL NORMALIZATION
    # ======================================================

    def _normalize_url(
        self,
        url: Optional[str],
        base_url: Optional[str],
    ) -> Optional[str]:
        if not url:
            return None

        # ❌ Ignore non-navigation URLs
        if url.startswith((
            "javascript:",
            "#",
            "mailto:",
            "tel:",
        )):
            return None

        return urljoin(base_url, url) if base_url else url
