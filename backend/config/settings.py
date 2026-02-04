from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    # ======================================================
    # 🔑 LLM CORE CONFIG (GLOBAL)
    # ======================================================

    GOOGLE_API_KEY: str = Field(
        ...,
        validation_alias="GEMINI_API_KEY",
        description="Google Gemini API key"
    )

    # --- Per-Agent Intelligence Assignment ---
    LLM_MODEL_DEFAULT: str = Field("models/gemini-1.5-flash", validation_alias="GEMINI_MODEL")
    LLM_MODEL_MAPPER: str = Field("models/gemini-1.5-pro", validation_alias="GEMINI_MODEL_MAPPER")
    LLM_MODEL_INTERACTION: str = Field("models/gemini-1.5-flash", validation_alias="GEMINI_MODEL_INTERACTION")
    LLM_MODEL_FORMS: str = Field("models/gemini-1.5-flash", validation_alias="GEMINI_MODEL_FORMS")
    LLM_MODEL_JS: str = Field("models/gemini-1.5-pro", validation_alias="GEMINI_MODEL_JS")

    LLM_TEMPERATURE: float = 0.2
    LLM_MAX_OUTPUT_TOKENS: int = 8192
    LLM_TIMEOUT_SECONDS: int = 10

    MAX_RETRIES: int = 3
    RETRY_DELAY_SECONDS: int = 2



    # ======================================================
    # 🕷️ EXECUTION CONFIG
    # ======================================================

    HEADLESS: bool = False
    ACTION_DELAY_MS: int = 1000

    # ======================================================
    # 📐 SAFETY LIMITS (HARD)
    # ======================================================

    MAX_UI_ELEMENTS: int = 60          # interaction extraction cap
    MAX_HISTORY_ITEMS: int = 20        # orchestrator memory safety
    
    BLOCKED_KEYWORDS: list = ["logout", "signout", "log out", "sign out", "payment", "subscribe", "follow"]

    # ======================================================
    # ⚙️ CRAWLER & AGENT LIMITS
    # ======================================================

    CRAWL_TIMEOUT_MS: int = 30000
    JS_FETCH_TIMEOUT_SECONDS: int = 10
    
    MAX_CRAWLED_PAGES: int = 500
    MAX_INTERACTIONS: int = 2000
    MAX_JS_SIZE_BYTES: int = 1_000_000  # 1MB
    
    AUTO_FILL_FORMS: bool = True

    BROWSER_SLOW_MO: int = 200
    BUTTON_CLICK_TIMEOUT: int = 5000
    MAX_SPA_STATES: int = 10
    
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000

    # ======================================================
    # 🗺️ MAPPER CONFIG
    # ======================================================

    HTML_CONTENT_LIMIT: int = 8000     # HTML chars sent to LLM
    COMPREHENSIVE_ANALYSIS_PROMPT: str = (
        "You are analyzing a web page. "
        "Extract all interactive elements."
    )

    # ======================================================
    # 🗄️ DATABASE
    # ======================================================

    DATABASE_URL: str = Field(
        ...,
        validation_alias="DATABASE_URL"
    )

    # ======================================================
    # 🧪 DEBUG / VERBOSE
    # ======================================================



    INTERACTION_VERBOSE_MODE: bool = False

    # ======================================================
    # Pydantic Settings Config
    # ======================================================

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        populate_by_name = True
        extra = "ignore"


# ======================================================
# 🔒 FAIL FAST ON STARTUP
# ======================================================

settings = Settings()
