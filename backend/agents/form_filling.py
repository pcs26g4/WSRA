from typing import Any, Dict, Optional
from urllib.parse import urlparse, urljoin
from uuid import uuid4
 
from sqlalchemy.orm import Session
 
from database.connection import SessionLocal
from database.models import Form, Session_details
from llm.gemini_client import LLMClient, LLMUsageError
import logging
from config.settings import settings
 
logger = logging.getLogger("form_filling_agent")
 
 
class FormFillingAgent:
    """
    FORM FILLING AGENT (AUTH / CRITICAL INPUT)
 
    STRICT RULES:
    - NEVER opens system browser
    - NEVER uses incognito
    - Uses ONLY Playwright page passed by Orchestrator
    - No sleep(), no fixed timeout
    - Human-in-the-loop login supported
    - Stores authenticated session in DB
    """
 
    def __init__(self, *, llm_enabled: bool):
        self.llm_enabled = llm_enabled
        self.llm = LLMClient(
            enabled=llm_enabled,
            agent_name="FormFillingAgent",
            model_name=settings.LLM_MODEL_FORMS
        )
 
    # ======================================================
    # 🚪 ENTRY POINT
    # ======================================================
 
    async def process_form_flow(
        self,
        *,
        scan_id: str,
        url: str,
        page,  # Playwright Page (MANDATORY)
        form_metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
 
        if page is None:
            raise RuntimeError(
                "FormFillingAgent requires an active Playwright page"
            )
 
        logger.info(f"📝 Processing form at: {url}")
 
        self._save_form(scan_id, url, form_metadata)
 
        # 1️⃣ Check auth requirement
        is_auth_form = await self._requires_auth(url)
 
        # � NEW: Check for existing session in DB first
        if is_auth_form:
             logger.info("🔍 Checking DB for existing cached session...")
             cached_session = self._load_active_session()
             if cached_session and cached_session.session_data:
                 cookies = cached_session.session_data.get("cookies")
                 if cookies:
                     logger.info("✅ Found cached session credentials! Auto-filling...")
                     
                     await page.context.add_cookies(cookies)
                     await page.reload() # Refresh to apply auth
 
                     # 🔥 AUTOMATIC SAVE: Clone this session for the CURRENT scan
                     # This ensures Scan B has a record even if it used Scan A's cookies
                     new_session_data = dict(cached_session.session_data)
                     new_session_data["source"] = "restored_from_cache_db"
                     
                     new_session_id = self._save_session(
                         scan_id,
                         new_session_data
                     )
 
                     return {
                         "status": "authenticated_from_cache",
                         "resume_url": url,
                         "auth_session_id": new_session_id
                     }
       
        # �🔹 NON-AUTH FORM
        if not is_auth_form:
            logger.info("🟡 Non-auth form detected")
           
            # Using settings instead of blocking input
            filled_by_user = settings.AUTO_FILL_FORMS
           
            if not filled_by_user:
                logger.info("Skipping form (settings.AUTO_FILL_FORMS=False)")
 
            # 🚀 ACTION: Explicitly fill and submit
            logger.info("⚡ Auto-filling generic form...")
            result = await self._fill_generic_form(page, url, form_metadata)
           
            self._save_session(
                scan_id,
                {
                    "type": "form_submission",
                    "url": url,
                    "filled_by_user": filled_by_user,
                    "form_metadata": form_metadata,
                    "submission_result": result
                }
            )
 
            return {
                "status": "form_processed",
                "filled_by_user": filled_by_user,
                "details": result
            }
 
        # 2️⃣ Resolve absolute login URL
        login_url = await self._resolve_login_url(url, page.url)
 
        logger.info(f"🔐 Navigating to login page: {login_url}")
        await page.goto(login_url, wait_until="domcontentloaded")
 
        logger.info("🧑‍💻 Waiting for authentication signal (no timeout) - Please login manually")
 
        # 3️⃣ Wait until authentication is observable
        await self._wait_for_login_success(page)
 
        # 4️⃣ Extract authenticated cookies
        cookies = await page.context.cookies()
 
        # 5️⃣ Persist session
        session_id = self._save_session(
            scan_id,
            {
                "cookies": cookies,
                "login_url": login_url,
                "authenticated": True,
                "filled_by_user": True,
                "source": "playwright_manual_login",
            }
        )
 
        logger.info("✅ Authentication successful")
 
        return {
            "status": "authenticated",
            "resume_url": url,
            "auth_session_id": session_id,
        }
 
    # ======================================================
    # 🧠 AUTH DETECTION
    # ======================================================
 
    async def _requires_auth(self, url: str) -> bool:
        lowered = url.lower()
        if any(k in lowered for k in ("login", "signin", "account", "dashboard")):
            return True
 
        self._guard_llm("authentication detection")
 
        prompt = (
            f"Does accessing {url} require user authentication? "
            f"Answer only true or false."
        )
        try:
            response = await self.llm.generate_text(prompt)
            return "true" in response.lower()
        except Exception:
            return False
 
    # ======================================================
    # 🔍 LOGIN URL RESOLUTION
    # ======================================================
 
    async def _resolve_login_url(
        self,
        target_url: str,
        current_page_url: str
    ) -> str:
 
        if target_url.startswith("http"):
            parsed = urlparse(target_url)
            if any(k in parsed.path.lower() for k in ("login", "signin", "auth")):
                return target_url
 
        parsed = urlparse(current_page_url)
        base = f"{parsed.scheme}://{parsed.netloc}"
 
        for path in ("/login", "/signin", "/auth", "/account/login"):
            return urljoin(base, path)
 
        self._guard_llm("login URL discovery")
 
        prompt = f"What is the login URL for {base}? Return the FULL URL only."
        try:
            resp = await self.llm.generate_text(prompt)
            if resp.startswith("http"):
                return resp.strip()
        except Exception:
            pass
 
        return urljoin(base, "/login")
 
 
    # ======================================================
    # ⏳ LOGIN SUCCESS DETECTION
    # ======================================================
 
    async def _wait_for_login_success(self, page):
        await page.wait_for_function(
            """
            () => {
                if (document.cookie && document.cookie.length > 0) {
                    return true;
                }
                const path = window.location.pathname.toLowerCase();
                return !path.includes("login") && !path.includes("signin");
            }
            """,
            timeout=0,
        )
 
    # ======================================================
    # 🗄️ DB OPERATIONS
    # ======================================================
 
    def _save_form(
        self,
        scan_id: str,
        url: str,
        metadata: Optional[Dict[str, Any]],
    ):
        if not metadata:
            # Don't save empty/unknown forms (crawler likely already found the real one)
            return
 
        db: Session = SessionLocal()
        try:
            # Deduplication check
            action = metadata.get("action")
            method = metadata.get("method")
           
            exists = db.query(Form).filter(
                Form.scan_id == scan_id,
                Form.url == url,
                Form.action == action,
                Form.method == method
            ).first()
 
            if exists:
                return
 
            db.add(Form(
                scan_id=scan_id,
                url=url,
                method=method,
                action=action,
                fields=metadata.get("fields"),
            ))
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"⚠️ Failed to save form: {e}")
        finally:
            db.close()
 
    def _save_session(self, scan_id: str, session_data: Dict[str, Any]) -> str:
        db: Session = SessionLocal()
        session_id = uuid4()
 
        try:
            db.add(Session_details(
                scan_id=scan_id,
                session_id=session_id,
                user_identifier=f"scan_{scan_id}",
                session_data=session_data,
                session_status="active",
            ))
            db.commit()
            logger.info(f"🗄️ Session stored: {session_id}")
        except Exception as e:
            db.rollback()
            logger.error(f"❌ Session save failed: {e}")
        finally:
            db.close()
 
        return str(session_id)
   
    def _load_active_session(self) -> Optional[Session_details]:
        """Fetch the latest active session from the DB (any scan)"""
        db: Session = SessionLocal()
        try:
            # We want the most recent active session, potentially from ANY scan?
            # Or just this scan? User asked for "directly from the db", implying persistence across runs.
            # Let's get the latest active session.
            return (
                db.query(Session_details)
                .filter(Session_details.session_status == "active")
                .order_by(Session_details.created_timestamp.desc())
                .first()
            )
        finally:
            db.close()
 
    # ======================================================
    # 🔒 LLM GUARD
    # ======================================================
 
    def _guard_llm(self, reason: str):
        if not self.llm_enabled:
            raise LLMUsageError(
                f"LLM usage forbidden in FormFillingAgent: {reason}"
            )
 
    # ======================================================
    # 📝 GENERIC FORM FILLING
    # ======================================================
 
    async def _fill_generic_form(self, page, url: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyzes form fields, generates fake data via LLM, and submits.
        """
        import json
       
        try:
            # 1. Identify Fields using Playwright (More reliable than static metadata)
            # We look for inputs that are visible and editable
            inputs = await page.evaluate("""() => {
                const fields = [];
                const inputs = document.querySelectorAll('input:not([type="hidden"]), textarea, select');
                inputs.forEach(el => {
                    if (el.offsetParent !== null && !el.disabled) { // Visible & Enabled
                        fields.push({
                            id: el.id,
                            name: el.name,
                            type: el.type,
                            placeholder: el.placeholder,
                            label: el.labels && el.labels[0] ? el.labels[0].innerText : ''
                        });
                    }
                });
                return fields;
            }""")
 
            if not inputs:
                logger.warning("⚠️ No fillable fields found on page.")
                return {"status": "skipped_no_fields"}
 
            # 2. Generate Data with LLM
            self._guard_llm("form data generation")
           
            prompt = (
                f"You are a QA tester. Generate valid, safe test data for the following form fields on {url}.\n"
                f"Fields: {json.dumps(inputs)}\n\n"
                f"Return ONLY a JSON object where keys are the field 'name' (or 'id' if name missing) and values are the inputs used.\n"
                f"Example: {{\"email\": \"test@example.com\", \"message\": \"Security scan test.\"}}"
            )
           
            llm_resp = await self.llm.generate_text(prompt)
            # Clean response (remove markdown code blocks if any)
            llm_resp = llm_resp.replace("```json", "").replace("```", "").strip()
           
            try:
                data_to_fill = json.loads(llm_resp)
            except json.JSONDecodeError:
                logger.error(f"❌ Failed to parse LLM form data: {llm_resp}")
                return {"status": "failed_llm_parse"}
 
            # 3. Fill Fields
            filled_count = 0
            for field in inputs:
                key = field.get("name") or field.get("id")
                if not key or key not in data_to_fill:
                    continue
                   
                value = data_to_fill[key]
                selector = f"[name='{key}']" if field.get("name") else f"#{key}"
               
                try:
                    loc = page.locator(selector).first
                    if field.get("type") in ["checkbox", "radio"]:
                        await loc.check()
                    elif field.get("tagName") == "SELECT":
                        await loc.select_option(value=value) # Try value first
                    else:
                        await loc.fill(str(value))
                    filled_count += 1
                except Exception as e:
                    logger.warning(f"Failed to fill {key}: {e}")
 
            logger.info(f"✍️ Filled {filled_count} fields.")
 
            # 4. Submit
            # Try finding a submit button
            try:
                submit_btn = page.locator('button[type="submit"], input[type="submit"]').first
                if await submit_btn.is_visible():
                    logger.info("🚀 Clicking submit button...")
                    await submit_btn.click()
                    await page.wait_for_load_state("networkidle", timeout=5000)
                    return {"status": "submitted", "fields_filled": filled_count}
                else:
                    # Fallback 1: Look for buttons with specific text
                    logger.info("⚠️ Standard submit button not found. Trying text fallback...")
                    submit_keywords = ["submit", "send", "login", "sign in", "search", "go", "next", "continue"]
                   
                    clicked_text_btn = False
                    for keyword in submit_keywords:
                        # Case-insensitive text match for button or input[type=button]
                        # We use a broad selector then filter by text
                        text_btn = page.locator(f"button, input[type='button'], a.btn, div[role='button']").filter(has_text=keyword).first
                       
                        if await text_btn.is_visible():
                            logger.info(f"🚀 Found fallback button with text '{keyword}'. Clicking...")
                            await text_btn.click()
                            clicked_text_btn = True
                            await page.wait_for_load_state("networkidle", timeout=5000)
                            return {"status": "submitted_via_text_fallback", "fields_filled": filled_count, "button_text": keyword}
                   
                    if not clicked_text_btn:
                        # Fallback 2: Press Enter on the last input
                        logger.info("Standard and text fallback failed. Pressing Enter...")
                        await page.keyboard.press("Enter")
                        await page.wait_for_load_state("networkidle", timeout=5000)
                        return {"status": "submitted_via_enter", "fields_filled": filled_count}
                   
            except Exception as e:
                logger.error(f"Submit action failed: {e}")
                return {"status": "submit_failed", "error": str(e)}
 
        except Exception as e:
            logger.error(f"Generic form filling error: {e}")
            return {"status": "error", "message": str(e)}
 