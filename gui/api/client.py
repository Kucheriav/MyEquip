import requests


class APIClient:
    BASE_URL = "http://localhost:8000/api"
    TOKEN: str | None = None

    @staticmethod
    def _headers() -> dict:
        if APIClient.TOKEN:
            return {"Authorization": f"Bearer {APIClient.TOKEN}"}
        return {}

    @staticmethod
    def get(endpoint):
        return requests.get(f"{APIClient.BASE_URL}{endpoint}", headers=APIClient._headers())

    @staticmethod
    def post(endpoint, data):
        return requests.post(f"{APIClient.BASE_URL}{endpoint}", json=data, headers=APIClient._headers())

    @staticmethod
    def put(endpoint, data):
        return requests.put(f"{APIClient.BASE_URL}{endpoint}", json=data, headers=APIClient._headers())

    @staticmethod
    def delete(endpoint):
        return requests.delete(f"{APIClient.BASE_URL}{endpoint}", headers=APIClient._headers())

    @staticmethod
    def login(email: str, password: str) -> tuple[bool, str]:
        """Authenticate against the API and store the token.
        Returns (ok, message)."""
        try:
            response = requests.post(
                f"{APIClient.BASE_URL}/auth/login",
                json={"email": email, "password": password},
            )
            if response.status_code == 200:
                APIClient.TOKEN = response.json()["access_token"]
                return True, "OK"
            detail = response.json().get("detail", "Ошибка авторизации")
            return False, str(detail)
        except Exception as e:
            return False, str(e)

    @staticmethod
    def is_auth_required() -> bool:
        """True when the server requires a token (GET /auth/me rejects us)."""
        try:
            return requests.get(
                f"{APIClient.BASE_URL}/auth/me", headers=APIClient._headers()
            ).status_code == 401
        except Exception:
            return False
