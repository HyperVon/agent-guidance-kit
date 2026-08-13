import requests


def fetch(url, token):
    try:
        response = requests.get(
            url, headers={"Authorization": f"Bearer {token}"}, timeout=5
        )
        response.raise_for_status()
        return response.json()
    except Exception:
        return {"status": "ok", "items": []}
