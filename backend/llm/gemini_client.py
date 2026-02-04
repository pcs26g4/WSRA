import json
import asyncio
from typing import Dict, Any, Optional
from uuid import UUID

from google import genai
from sqlalchemy.orm import Session

from config.settings import settings
from database.models import LLMRequest


class LLMUsageError(RuntimeError):
    """Raised when LLM is used against policy."""
    pass


class LLMClient:
    """
    CENTRALIZED GEMINI CLIENT

    HARD RULES:
    - LLM NEVER controls loops
    - LLM NEVER returns crawl decisions
    - LLM NEVER executes actions
    - LLM ONLY reasons, ranks, explains
    """

    def __init__(
        self,
        *,
        enabled: bool,
        agent_name: str,
        model_name: Optional[str] = None,
        temperature: Optional[float] = None,
    ):
        self.enabled = enabled
        self.agent_name = agent_name

        if not enabled:
            self.client = None
            return

        if not settings.GOOGLE_API_KEY:
            raise RuntimeError("GOOGLE_API_KEY missing but LLM usage was enabled")

        self.client = genai.Client(api_key=settings.GOOGLE_API_KEY)
        self.model_name = model_name or settings.LLM_MODEL_DEFAULT
        self.temperature = temperature if temperature is not None else settings.LLM_TEMPERATURE

    # ======================================================
    # 🔒 HARD GUARD
    # ======================================================

    def _guard(self, reason: str):
        if not self.enabled:
            raise LLMUsageError(
                f"LLM usage forbidden for agent '{self.agent_name}': {reason}"
            )

    # ======================================================
    # 🔁 GEMINI CALL
    # ======================================================

    async def _call_gemini(self, prompt: str) -> str:
        self._guard("Gemini API call")

        for attempt in range(settings.MAX_RETRIES):
            try:
                response = await asyncio.to_thread(
                    self.client.models.generate_content,
                    model=self.model_name,
                    contents=prompt,
                    config={
                        "temperature": self.temperature,
                        "max_output_tokens": settings.LLM_MAX_OUTPUT_TOKENS,
                    },
                )
                return (response.text or "").strip()

            except Exception as exc:
                if attempt == settings.MAX_RETRIES - 1:
                    raise RuntimeError(f"Gemini failed: {exc}")
                await asyncio.sleep(settings.RETRY_DELAY_SECONDS * (attempt + 1))

        return ""

    # ======================================================
    # 🧠 GENERIC TEXT
    # ======================================================

    async def generate_text(self, prompt: str) -> str:
        try:
            return await self._call_gemini(prompt)
        except Exception:
            return ""

    # ======================================================
    # 🧠 INTERACTION REASONING
    # ======================================================

    async def decide_next_interaction(
        self,
        *,
        input_data: Dict[str, Any],
        db: Optional[Session] = None,
    ) -> Dict[str, Any]:
        self._guard("interaction reasoning")

        prompt = f"""
Return STRICT JSON ONLY.

Rules:
- Do NOT invent URLs
- Do NOT suggest login, signup, payment
- Prefer safe navigation
- ONE action only

INPUT:
{json.dumps(input_data, indent=2)}
"""

        response_text = ""
        status = "failed"
        error = None
        parsed: Dict[str, Any] = {}

        try:
            response_text = await self._call_gemini(prompt)
            parsed = self._parse_json(response_text)
            status = "success"
        except Exception as exc:
            error = str(exc)

        if db:
            self._log_llm_call(
                db=db,
                scan_id=input_data.get("scan_id"),
                url=input_data.get("current_page_url"),
                prompt=prompt,
                response=response_text,
                status=status,
                error=error,
            )

        if status != "success":
            raise RuntimeError(f"Interaction LLM failed: {error}")

        return parsed

    # ======================================================
    # 🧩 JSON PARSER
    # ======================================================

    def _parse_json(self, text: str) -> Any:
        if not text:
            return {}

        cleaned = text.replace("```json", "").replace("```", "").strip()

        try:
            return json.loads(cleaned)
        except Exception:
            start, end = cleaned.find("{"), cleaned.rfind("}")
            if start != -1 and end != -1:
                try:
                    return json.loads(cleaned[start:end + 1])
                except Exception:
                    pass
        return {}

    # ======================================================
    # 🧾 DB LOGGING
    # ======================================================

    def _log_llm_call(
        self,
        *,
        db: Session,
        scan_id: Optional[str],
        url: Optional[str],
        prompt: str,
        response: str,
        status: str,
        error: Optional[str],
    ):
        try:
            if not scan_id:
                return

            db.add(
                LLMRequest(
                    scan_id=UUID(scan_id),
                    agent_name=self.agent_name,
                    url=url,
                    prompt=prompt,
                    response=response,
                    status=status,
                    error=error,
                )
            )
            db.commit()
        except Exception:
            db.rollback()
