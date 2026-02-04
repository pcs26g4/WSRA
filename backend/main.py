import sys
import os
import uvicorn
from api.main import app
from config.settings import settings

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)

if __name__ == "__main__":
    uvicorn.run(
        "api.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=True,
    )
    