import os


ALLOW_GUESTS = os.getenv("ALLOW_GUESTS", "true").lower() == "true"
SERVICE_TOKEN = os.getenv("SERVICE_TOKEN", "dev-token")
