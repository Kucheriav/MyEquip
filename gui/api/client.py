import logging

import requests

# One shared session -> TCP connections are reused (keep-alive) instead of
# opening a new connection for every single request.
_session = requests.Session()

logger = logging.getLogger("gui.api")


class APIClient:
    # 127.0.0.1 instead of 'localhost': skips the slow IPv6 lookup attempt
    BASE_URL = "http://127.0.0.1:8000/api"
    TOKEN: str | None = None
    # Current user profile from /auth/me: role + club_ids + personal data
    ME: dict | None = None

    @staticmethod
    def _headers() -> dict:
        if APIClient.TOKEN:
            return {"Authorization": f"Bearer {APIClient.TOKEN}"}
        return {}

    # ---------- current user ----------
    @staticmethod
    def fetch_me() -> dict | None:
        """Load and cache the current user profile (role, clubs)."""
        try:
            response = APIClient.get("/auth/me")
            if response.status_code == 200:
                APIClient.ME = response.json()
        except Exception:
            logger.warning("fetch_me failed", exc_info=True)
            APIClient.ME = None
        return APIClient.ME

    @staticmethod
    def role() -> str:
        return (APIClient.ME or {}).get("role", "tourist")

    @staticmethod
    def is_leader() -> bool:
        return APIClient.role() == "leader"

    @staticmethod
    def is_staff() -> bool:
        return APIClient.role() in ("leader", "storekeeper")

    @staticmethod
    def my_club_ids() -> list:
        return (APIClient.ME or {}).get("club_ids", [])

    @staticmethod
    def _request(method: str, endpoint: str, **kwargs):
        try:
            response = _session.request(
                method, f"{APIClient.BASE_URL}{endpoint}", **kwargs)
        except Exception:
            logger.exception("%s %s failed", method, endpoint)
            raise
        if response.status_code >= 400:
            logger.warning("%s %s -> %s", method, endpoint, response.status_code)
        return response

    @staticmethod
    def get(endpoint):
        return APIClient._request("GET", endpoint, headers=APIClient._headers())

    @staticmethod
    def post(endpoint, data):
        return APIClient._request(
            "POST", endpoint, json=data, headers=APIClient._headers())

    @staticmethod
    def put(endpoint, data):
        return APIClient._request(
            "PUT", endpoint, json=data, headers=APIClient._headers())

    @staticmethod
    def delete(endpoint):
        return APIClient._request(
            "DELETE", endpoint, headers=APIClient._headers())

    @staticmethod
    def login(login: str, password: str) -> tuple[bool, str]:
        """Authenticate against the API and store the token.
        Returns (ok, message)."""
        try:
            response = APIClient._request(
                "POST", "/auth/login",
                json={"login": login, "password": password},
            )
            if response.status_code == 200:
                APIClient.TOKEN = response.json()["access_token"]
                APIClient.fetch_me()
                return True, "OK"
            detail = response.json().get("detail", "Ошибка авторизации")
            return False, str(detail)
        except Exception as e:
            return False, str(e)

    @staticmethod
    def register(data: dict) -> tuple[bool, str]:
        """Register a leader with an invite code, then log in.
        Returns (ok, message)."""
        try:
            response = APIClient._request(
                "POST", "/auth/register", json=data)
            if response.status_code != 201:
                return False, response.json().get("detail", "Ошибка регистрации")
            return APIClient.login(data["phone"], data["password"])
        except Exception as e:
            return False, str(e)

    @staticmethod
    def is_auth_required() -> bool:
        """True when the server requires a token (GET /auth/me rejects us)."""
        try:
            return _session.get(
                f"{APIClient.BASE_URL}/auth/me", headers=APIClient._headers()
            ).status_code == 401
        except Exception:
            return False
