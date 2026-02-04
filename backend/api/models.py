from pydantic import BaseModel, HttpUrl

class ScanRequest(BaseModel):
    url: HttpUrl
    use_llm: bool = True  # kept for backward compatibility

class ScanResponse(BaseModel):
    scan_id: str
    status: str
    message: str
