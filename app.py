"""CLI/ASGI entry point. Run with python app.py or uvicorn app:app."""
import os
import uvicorn
from adrobot.api.app import create_app

PORT = int(os.getenv("PORT", "8000"))
app = create_app(PORT)

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=PORT)
