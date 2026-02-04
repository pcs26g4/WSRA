import asyncio
import uuid
from datetime import datetime, timezone
from collections import deque
from typing import Any, Deque, Dict, Set, Optional
from urllib.parse import urlparse, urljoin
from sqlalchemy.orm import Session
import logging
import hashlib
import json
import re

from config.settings import settings
from llm.policy import LLMPermission
from database.connection import SessionLocal
from database.models import Scan, HtmlPage, InteractionTarget, InteractionOutcome
from agents.crawler import run_crawler
from agents.mapper import MapperAgent
from agents.interaction_agent import InteractionAgent
from agents.vuln_hinter import VulnHinterAgent
from agents.js_analyzer import JSAnalyzerAgent
from agents.form_filling import FormFillingAgent
from agents.network_monitor import NetworkMonitor
from exports.burp_exporter import BurpExporterAgent # FIXED: from agents -> exports

# Setup Logger
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
logger = logging.getLogger("orchestrator")

class Orchestrator:
    def __init__(self, target_url: str, scan_id: str):
        self.target_url = target_url
        self.scan_id = scan_id
        
        # State
        self.frontier: Deque[str] = deque([target_url])
        self.frontier_set: Set[str] = {target_url} # 👈 Track unique frontier URLs
        self.crawled_urls: Set[str] = set()
        self.visited_states: Set[str] = set() # For SPA states
        self.domain = urlparse(target_url).netloc
        self.failure_counts: Dict[str, int] = {} # Track crawl failures

        # Agents
        policy = LLMPermission()
        self.mapper = MapperAgent(llm_enabled=policy.mapper)
        self.interaction_agent = InteractionAgent(llm_enabled=policy.interaction)
        self.js_analyzer = JSAnalyzerAgent(scan_id=scan_id, llm_enabled=policy.js_analyzer) 
        self.form_agent = FormFillingAgent(llm_enabled=policy.form_filling)
        self.vuln_hinter = VulnHinterAgent(scan_id=scan_id)
        self.network_monitor = NetworkMonitor(scan_id=scan_id)
        self.burp_exporter = BurpExporterAgent()

    async def run(self):
        """
        Main Loop:
        1. Initialize Scan
        2. Pop URL from Frontier
        3. Crawl Page (Playwright)
        4. Analyze (Mapper, Vuln, JS)
        5. Interact (Click buttons, submit forms) -> New URLs/States -> Frontier
        6. Repeat until Frontier entry or limit
        7. Finalize
        """
        db = SessionLocal()
        try:
            logger.info(f"🚀 Starting scan for {self.target_url}")
            self._initialize_scan(db)

            # Initialize Browser/Context ONCE
            await self.network_monitor.get_page()

            count = 0
            while self.frontier and count < settings.MAX_CRAWLED_PAGES:
                current_url = self.frontier.popleft()
                
                if current_url in self.crawled_urls:
                    continue

                # 🔥 LOG: FRONTIER STATUS
                logger.info(f"📋 CURRENT FRONTIER QUEUE ({len(self.frontier)}): {list(self.frontier)}")

                logger.info(f"🕷️ Crawling: {current_url} ({count + 1}/{settings.MAX_CRAWLED_PAGES})")

                # A. CRAWL PHASE
                # Pass SHARED Context to crawler for persistence
                context = self.network_monitor._context
                
                crawl = await run_crawler(
                    url=current_url,
                    db=db,
                    scan_id=self.scan_id,
                    context=context # 👈 PERSISTENT CONTEXT
                )
                
                if crawl.get("status") != "success":
                    # 🔄 RETRY LOGIC
                    fail_count = self.failure_counts.get(current_url, 0)
                    if fail_count < settings.MAX_RETRIES:
                        self.failure_counts[current_url] = fail_count + 1
                        self.frontier.append(current_url)
                        logger.warning(f"⚠️ Crawl failed for {current_url}, retrying ({fail_count + 1}/{settings.MAX_RETRIES})")
                    else:
                        logger.error(f"❌ Crawl failed permanently for {current_url}")
                        self.crawled_urls.add(current_url) # Mark as done to stop trying
                    continue
                
                # ✅ SUCCESS
                self.crawled_urls.add(current_url)
                
                # Handle Redirects
                final_url = crawl.get("final_url", current_url)
                if final_url != current_url:
                    logger.info(f"🔀 Redirected: {current_url} -> {final_url}")
                    self.crawled_urls.add(final_url)
                
                count += 1
                
                # B. ANALYSIS PHASE (Parallel)
                self._log_audit(db, "Mapper", "started", f"Analyzing DOM structure for {final_url}")
                logger.info(f"🗺️ Generating Sitemap for {final_url}...")
                tasks = [
                    self.mapper.generate_sitemap_from_scan(self.scan_id), # Efficient update
                    # self.vuln_hunter.analyze_page(final_url, crawl["html"]), # DISABLED: Missing Agent
                    self._analyze_new_js_files(db, final_url)
                ]
                await asyncio.gather(*tasks)
                logger.info(f"✅ Sitemap Updated. Starting Interaction Phase...")

                # C. INTERACTION PHASE (Dynamic Discovery)
                await self._interaction_phase(db, current_url=final_url)
            
            logger.info("🏁 Scan completed!")
        
        except Exception as e:
            logger.error(f"❌ Scan failed: {e}", exc_info=True)
            # Update scan status to failed?
        finally:
            await self._finalize_scan(db)
            await self.network_monitor.close()
            db.close()

    async def _analyze_new_js_files(self, db: Session, url: str):
        """Trigger JS Agent on JS files found on this page"""
        try:
           self._log_audit(db, "JSAnalyzer", "started", f"Analyzing JavaScript assets on {url}")
           # logger.info(f"📜 Analyzing JS for {url}") 
           await self.js_analyzer.analyze_latest_files(db)
           self._log_audit(db, "JSAnalyzer", "completed", f"Finished JS analysis for {url}")
        except Exception as e:
           logger.error(f"JS Analysis error: {e}")

    def _canonicalize_url(self, url: str) -> str:
        """
        Normalize URL for validation.
        - Supports Standard URLs (ignores #anchor)
        - Supports SPA URLs (preserves #/route or #!/route)
        """
        try:
            parsed = urlparse(url)
            scheme = parsed.scheme.lower()
            netloc = parsed.netloc.lower()
            path = parsed.path
            
            # Normalize trailing slash (except for root /)
            if len(path) > 1 and path.endswith('/'):
                path = path.rstrip('/')
            
            clean_url = f"{scheme}://{netloc}{path}"
            
            if parsed.query:
                clean_url += f"?{parsed.query}"
                
            # 🔥 SPA SUPPORT: Keep fragment if it looks like a route
            if parsed.fragment:
                if parsed.fragment.startswith("/") or parsed.fragment.startswith("!"):
                    clean_url += f"#{parsed.fragment}"
            
            return clean_url
        except:
            return url

    async def _interaction_phase(self, db: Session, current_url: str):
        """
        1. Fetch unvisited targets from DB (Mapper output)
        2. Execute actions (Click/Submit)
        3. Capture new states/URLs
        """
        # 🚀 OPTIMIZATION: Filter targets by current URL
        all_targets = db.query(InteractionTarget).filter(
            InteractionTarget.scan_id == uuid.UUID(self.scan_id),
            InteractionTarget.visited == False
        ).all()
        
        targets = [
            t for t in all_targets
            if t.source_url == current_url or t.source_url == current_url.rstrip('/')
        ]

        logger.info(f"🖱️ Found {len(targets)} interaction targets on {current_url}")
        if targets:
            self._log_audit(db, "InteractionAgent", "started", f"Identified {len(targets)} interactive elements on {current_url}")

        for target_row in targets:
            if self.interaction_count >= settings.MAX_INTERACTIONS:
                break

            target = {
                "id": str(target_row.id),
                "type": target_row.element_type,
                "selector": target_row.element_selector,
                "source_url": target_row.source_url,
                "attributes": target_row.attributes_json
            }
            
            # 🚀 FAST-TRACK LINKS (Don't click, just crawl)
            if target["type"] == "navigate" or target["type"] == "link":
                raw_dest = target["attributes"].get("destination") or target["attributes"].get("href")
                if raw_dest:
                     # Resolve relative URLs
                    dest = urljoin(target["source_url"], raw_dest)
                    # Canonicalize for deduplication
                    canon_dest = self._canonicalize_url(dest)

                    # KEYWORD BLOCKING (Aggressive Normalization)
                    # Normalize URL: lowercase, remove special chars
                    normalized_dest = re.sub(r'[^a-z0-9]', '', canon_dest.lower())
                    
                    # Normalize keywords (cache this ideally, but fine here)
                    # "sign out" -> "signout", "log-out" -> "logout"
                    blocked_triggers = [re.sub(r'[^a-z0-9]', '', k) for k in settings.BLOCKED_KEYWORDS]
                    
                    if any(trigger in normalized_dest for trigger in blocked_triggers):
                        logger.info(f"🚫 Blocked URL by keyword: {canon_dest}")
                        self._log_audit(db, "InteractionAgent", "blocked", f"Skipped interaction with blocked URL: {canon_dest}")
                        self._mark_interacted(db, target, dest)
                        continue

                    if self._is_in_scope(canon_dest) and canon_dest not in self.crawled_urls and canon_dest not in self.frontier_set:
                        self.frontier.append(canon_dest)
                        self.frontier_set.add(canon_dest)
                        logger.info(f"🔗 Added new URL to frontier: {canon_dest}")
                        logger.info(f"🖱️ Found {len(targets)} interaction targets on {current_url}")
                        self._log_audit(db, "InteractionAgent", "discovered", f"Discovered new URL: {canon_dest}")
                
                    self._mark_interacted(db, target, dest)
                continue

            # ... result of interaction logic ...
            self.interaction_count += 1
            
            self._log_audit(db, "InteractionAgent", "interacting", f"Interacting with [{target['type']}] {target['selector']}")
            result = await self.interaction_agent.execute_action(target)

            # ---------------------------------
            # FORM → delegate
            # ---------------------------------
            if result["status"] == "form_detected":
                try:
                    self._log_audit(db, "FormAgent", "started", f"Processing detected form on {current_url}")
                    # 🔥 FIXED: Get valid page from network monitor
                    page = await self.network_monitor.get_page()
                    
                    await self.form_agent.process_form_flow(
                        scan_id=self.scan_id,
                        url=target.get("target_url") or target["source_url"],
                        page=page,  # 👈 Passed active page
                    )
                    self._log_audit(db, "FormAgent", "completed", "Form processing sequence finished")
                except Exception as e:
                    logger.error(f"Form processing failed: {e}")
                    self._log_audit(db, "FormAgent", "error", f"Form processing failed: {e}")
                
                self._mark_interacted(db, target, None)
                continue

            new_url = result.get("new_url")
            
            # ---------------------------------
            # LINK/NAVIGATE → Add to frontier
            # ---------------------------------
            if new_url:
                canon_new = self._canonicalize_url(new_url)
                if canon_new not in self.crawled_urls and canon_new not in self.frontier_set:
                     # 🔥 FIXED: Add discovered links to frontier
                     if self._is_in_scope(canon_new):
                         self.frontier.append(canon_new)
                         self.frontier_set.add(canon_new)
                         logger.info(f"🔗 NEW URL DISCOVERED & ADDED TO FRONTIER: {canon_new} 🚀")
                         self._log_audit(db, "InteractionAgent", "discovery", f"Interaction revealed new URL: {canon_new}")


        # ---------------------------------
        # BUTTON → SPA click
        # ---------------------------------
            if target["type"] == "button":
                selector = target["selector"] # 👈 Define selector here
                self._log_audit(db, "InteractionAgent", "click", f"Simulating click on: {selector}")
                # 🔥 FIXED: Use NetworkMonitor to get page, not run_crawler function
                try:
                    page = await self.network_monitor.get_page()  # 👈 CRITICAL FIX
                    if page.is_closed():
                        logger.warning("⚠️ Page was closed, re-initializing...")
                        # Ideally network_monitor would handle this, but as safeguard:
                        page = await self.network_monitor._context.new_page()
                except Exception as e:
                    logger.error(f"Failed to get runtime page: {e}")
                    continue

                try:
                    await page.goto(target["source_url"])
                except Exception as e:
                    logger.error(f"❌ Navigation failed (Page closed?): {e}")
                    self._mark_interacted(db, target, None)
                    continue

                # 🔥 Strict Mode Handling: Use .first if ambiguous
                locator = page.locator(selector).first

                try:
                    is_visible = await locator.is_visible()
                except Exception as e:
                    logger.warning(f"⚠️ Locator visibility check failed (skipping): {selector} - {e}")
                    self._mark_interacted(db, target, None)
                    continue

                if not is_visible:
                    # logger.warning(f"⚠️ Invisible button skipped: {selector}")
                    self._mark_interacted(db, target, None)
                    continue

                try:
                    await locator.click(timeout=settings.BUTTON_CLICK_TIMEOUT) # 👈 settings
                except Exception as e:
                    logger.error(f"⚠️ Button click failed: {e}", exc_info=False) # Log error but don't spam stacktrace
                    self._mark_interacted(db, target, None)
                    continue

                try:
                    await page.wait_for_load_state("domcontentloaded")
                except Exception:
                    pass

                runtime_url = page.url
                state_fp = await self._compute_state_fingerprint(page)
                state_key = f"{runtime_url}:{state_fp}"

                if state_key not in self.visited_states:
                    # logger.info(f"🔁 New SPA state: {runtime_url}")
                    self.visited_states.add(state_key)

                    if runtime_url not in self.crawled_urls:
                        self.frontier.append(runtime_url)
                        self._log_audit(db, "InteractionAgent", "state_change", f"SPA State Change: {runtime_url}")

                new_url = runtime_url

        # ---------------------------------
        # FINALIZE INTERACTION
        # ---------------------------------
            self._mark_interacted(db, target, new_url)

    async def _compute_state_fingerprint(self, page) -> str:
        # SPA State = URL + DOM Hash
        try:
             # Fast state check: Text content + Title
             # Removing dynamic content like timestamps might be needed
             text = await page.evaluate("document.body.innerText")
             return hashlib.sha256(text.encode("utf-8")).hexdigest()
        except:
            return "unknown_state"

    def _mark_interacted(self, db: Session, target: dict, new_url: Optional[str]):
        t_row = db.query(InteractionTarget).filter(
            InteractionTarget.id == uuid.UUID(target["id"])
        ).first()
        if t_row:
            t_row.visited = True
        
        db.add(
            InteractionOutcome(
                scan_id=uuid.UUID(self.scan_id),
                action_type=target["type"],
                element_selector=target["selector"],
                previous_url=target.get("source_url"),
                new_url=new_url,
            )
        )
        db.commit()

    def _log_audit(self, db: Session, agent: str, action: str, message: str):
        from database.models import AuditLog
        try:
            db.add(AuditLog(
                scan_id=uuid.UUID(self.scan_id),
                agent=agent,
                action=action,
                details={"message": message}
            ))
            db.commit()
        except Exception as e:
            logger.error(f"Failed to log audit: {e}")

    def _initialize_scan(self, db: Session):
        scan = db.query(Scan).filter(
            Scan.id == uuid.UUID(self.scan_id)
        ).first()

        if not scan:
            scan = Scan(
                id=uuid.UUID(self.scan_id),
                target_domain=self.target_url,
                status="RUNNING",
                started_at=datetime.now(timezone.utc), # 👈 timezone aware
            )
            db.add(scan)

        scan.status = "RUNNING"
        db.commit()

    async def _finalize_scan(self, db: Session):
        scan = db.query(Scan).filter(
            Scan.id == uuid.UUID(self.scan_id)
        ).first()

        if scan:
            scan.status = "COMPLETED"
            scan.completed_at = datetime.now(timezone.utc) # 👈 timezone aware
            db.commit()

        # 🔥 Run Vulnerability Hinter (Analysis Phase)
        try:
            # We run this synchronously or await if async? 
            # In vuln_hinter.py, run(db) is async def run(self, db).
            await self.vuln_hinter.run(db)
        except Exception as e:
            logger.error(f"Vulnerability Hinter failed: {e}")

        self.burp_exporter.export_scan(
            self.scan_id,
        )

        # 🔥 NEW: Generate Multi-Format Reports
        from exports.report_generator import ReportGeneratorAgent # FIXED: from agents -> exports
        reporter = ReportGeneratorAgent()
        paths = reporter.generate_reports(self.scan_id)
        logger.info(f"📊 Reports generated: {paths}")

    def _is_in_scope(self, url: str) -> bool:
        try:
            parsed = urlparse(url)
            # 1. Strip www. from both for comparison
            target_domain_clean = self.domain.replace("www.", "")
            check_domain_clean = parsed.netloc.replace("www.", "")
            
            # 2. Allow if one ends with the other (subdomain match)
            # e.g. "app.snappod.ai".endswith("snappod.ai") -> True
            return (
                target_domain_clean in check_domain_clean or 
                check_domain_clean.endswith(target_domain_clean)
            )
        except:
            return False
    
    @property
    def interaction_count(self) -> int:
        if not hasattr(self, "_interaction_count"):
            self._interaction_count = 0
        return self._interaction_count
    
    @interaction_count.setter
    def interaction_count(self, value):
        self._interaction_count = value
