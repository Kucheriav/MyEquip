"""Smoke test for the web UI (vertical slice).

Run against a freshly created empty database with the server started on
a non-default port, exactly like scripts/smoke_test.py:

    $env:DB_NAME='my_equip_test'
    .\\.venv\\Scripts\\python.exe -m uvicorn app.main:app --port 8001
    .\\.venv\\Scripts\\python.exe scripts/web_smoke.py http://127.0.0.1:8001

Checks the browser flow (login by cookie, issue, accept) and that the
forms cannot override the "executor is the logged-in user" rule.
"""
import sys
from datetime import date, timedelta
from pathlib import Path

import requests

BASE_URL = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000").rstrip("/")
STAMP = str(int(__import__("time").time()))
INVITE_FILE = Path(__file__).resolve().parent.parent / "invite_code.txt"

FAILURES = []


def check(name, condition, details=""):
    if condition:
        print(f"PASS  {name}")
    else:
        print(f"FAIL  {name}" + (f": {details}" if details else ""))
        FAILURES.append(name)
    return condition


def expect(name, response, status):
    return check(name, response.status_code == status,
                 f"got {response.status_code}, expected {status}: {response.text[:200]}")


def main():
    if not INVITE_FILE.exists():
        print(f"No {INVITE_FILE.name}: run this against an empty database")
        return 2
    invite = INVITE_FILE.read_text(encoding="utf-8").splitlines()[1].strip()

    leader_phone = f"+7999{STAMP[-7:]}"
    leader_password = "Web-pass1"
    api = requests.Session()

    # ---------- 1. API setup: leader, club, storages, category, item, tourist ----------
    expect("leader registers with the bootstrap invite", api.post(
        f"{BASE_URL}/api/auth/register", json={
            "name": "Веб", "surname": "Лидер", "phone": leader_phone,
            "password": leader_password, "invite_code": invite,
        }), 201)

    login = api.post(f"{BASE_URL}/api/auth/login",
                     json={"login": leader_phone, "password": leader_password})
    expect("leader logs in through the API", login, 200)
    token = login.json()["access_token"]
    auth = {"Authorization": f"Bearer {token}"}
    me = api.get(f"{BASE_URL}/api/auth/me", headers=auth).json()
    leader_id = me["id"]

    club = api.post(f"{BASE_URL}/api/clubs/", headers=auth,
                    json={"name": f"web-club-{STAMP}"}).json()
    club_id = club["id"]
    storage1 = api.post(f"{BASE_URL}/api/storages/", headers=auth,
                        json={"name": "Веб-склад 1", "club_id": club_id}).json()
    storage2 = api.post(f"{BASE_URL}/api/storages/", headers=auth,
                        json={"name": "Веб-склад 2", "club_id": club_id}).json()
    category = api.post(f"{BASE_URL}/api/categories/", headers=auth,
                        json={"title": "Веб-категория", "club_id": club_id}).json()
    item = api.post(f"{BASE_URL}/api/items/", headers=auth, json={
        "name": "Веб-рюкзак", "category_id": category["id"],
        "storage_id": storage1["id"],
    }).json()
    item_id = item["id"]

    tourist = api.post(f"{BASE_URL}/api/users/", headers=auth, json={
        "name": "Турист", "surname": "Вебов", "phone": f"+7888{STAMP[-7:]}",
        "club_id": club_id,
    }).json()
    tourist_id = tourist["id"]

    # ---------- 2. Browser session ----------
    browser = requests.Session()
    anonymous = requests.Session()

    redirect = anonymous.get(f"{BASE_URL}/app/items", allow_redirects=False)
    check("anonymous page redirects to /login",
          redirect.status_code == 303 and "/login" in redirect.headers.get("location", ""),
          f"{redirect.status_code} {redirect.headers.get('location')}")

    page = anonymous.get(f"{BASE_URL}/login")
    expect("login page renders", page, 200)
    check("login page has the form", 'action="/login"' in page.text, page.text[:200])

    form_login = browser.post(f"{BASE_URL}/login", allow_redirects=False, data={
        "login": leader_phone, "password": leader_password, "next": "/app/items",
    })
    check("web login sets a session cookie and redirects",
          form_login.status_code == 303
          and "myequip_session" in browser.cookies
          and "myequip_csrf" in browser.cookies,
          f"{form_login.status_code} cookies={list(browser.cookies.keys())}")

    csrf = browser.cookies.get("myequip_csrf")

    items_page = browser.get(f"{BASE_URL}/app/items")
    expect("items page renders", items_page, 200)
    check("items page lists the item", "Веб-рюкзак" in items_page.text)
    check("items page shows a Russian status", "Доступен" in items_page.text)
    check("navigation shows the logged-in leader",
          "Лидер Веб" in items_page.text and "Руководитель" in items_page.text)
    check("static assets are served", browser.get(f"{BASE_URL}/static/app.css").status_code == 200)

    filtered = browser.get(f"{BASE_URL}/app/items", params={"status": "maintenance"})
    check("status filter is applied", filtered.status_code == 200 and "Веб-рюкзак" not in filtered.text)

    # ---------- 3. Issue through the web form ----------
    dist_page = browser.get(f"{BASE_URL}/app/distributions")
    expect("distributions page renders", dist_page, 200)
    check("getter list contains a club member", "Турист" in dist_page.text, dist_page.text[:200])

    fragment = browser.get(f"{BASE_URL}/app/distributions/getters", params={"item_id": item_id})
    check("HTMX getter fragment returns the club member",
          fragment.status_code == 200 and "Турист" in fragment.text,
          fragment.text[:200])

    issued = browser.post(f"{BASE_URL}/app/distributions", allow_redirects=False, data={
        "item_id": item_id,
        "getter_id": tourist_id,
        "expiration_date": (date.today() + timedelta(days=7)).isoformat(),
        "comment": "веб-выдача",
        "csrf_token": csrf,
        # A spoofed giver must be ignored: the page always uses the session user
        "giver_id": tourist_id,
    })
    check("issue redirects back with a success flash",
          issued.status_code == 303 and "ok=issued" in issued.headers.get("location", ""),
          f"{issued.status_code} {issued.headers.get('location')}")

    distributions = api.get(f"{BASE_URL}/api/distributions/", headers=auth).json()
    record = max(distributions, key=lambda row: row["id"])
    check("distribution is stored with the logged-in leader as giver",
          record["giver_id"] == leader_id and record["getter_id"] == tourist_id,
          record)
    item_after_issue = api.get(f"{BASE_URL}/api/items/{item_id}", headers=auth).json()
    check("item becomes 'issued'", item_after_issue["status"] == "issued",
          item_after_issue["status"])

    # ---------- 4. Accept through the web form ----------
    accepted = browser.post(
        f"{BASE_URL}/app/distributions/{record['id']}/accept",
        allow_redirects=False, data={
            "storage_id": storage2["id"],
            "accepting_date": date.today().isoformat(),
            "csrf_token": csrf,
            "accepter_id": tourist_id,  # must be ignored as well
        })
    check("accept redirects back with a success flash",
          accepted.status_code == 303 and "ok=accepted" in accepted.headers.get("location", ""),
          f"{accepted.status_code} {accepted.headers.get('location')}")

    returned = api.get(f"{BASE_URL}/api/distributions/{record['id']}", headers=auth).json()
    check("distribution is returned and accepted by the leader",
          returned["status"] == "returned" and returned["accepter_id"] == leader_id,
          returned)
    item_after_return = api.get(f"{BASE_URL}/api/items/{item_id}", headers=auth).json()
    check("item is available again on the chosen storage",
          item_after_return["status"] == "available"
          and item_after_return["storage_id"] == storage2["id"],
          item_after_return)

    text_page = browser.get(f"{BASE_URL}/app/distributions")
    check("history shows the returned status in Russian", "Возвращён" in text_page.text)

    # ---------- 5. Protection ----------
    no_csrf = browser.post(f"{BASE_URL}/app/distributions", allow_redirects=False, data={
        "item_id": item_id, "getter_id": tourist_id,
        "expiration_date": date.today().isoformat(),
    })
    expect("form without a CSRF token is rejected", no_csrf, 400)

    bad_login = requests.post(f"{BASE_URL}/login", allow_redirects=False, data={
        "login": leader_phone, "password": "wrong", "next": "/app/items",
    })
    check("wrong password does not create a session",
          bad_login.status_code == 401 and "myequip_session" not in bad_login.cookies,
          bad_login.status_code)

    # ---------- 6. Storekeeper gets staff pages ----------
    invite_resp = api.post(f"{BASE_URL}/api/invites/", headers=auth,
                           json={"role": "storekeeper", "club_id": club_id})
    expect("leader creates a storekeeper invite", invite_resp, 201)
    sk_phone = f"+7777{STAMP[-7:]}"
    expect("storekeeper registers with the invite", api.post(
        f"{BASE_URL}/api/auth/register", json={
            "name": "Склад", "surname": "Завхозов", "phone": sk_phone,
            "password": "Web-pass2", "invite_code": invite_resp.json()["code"],
        }), 201)

    sk_browser = requests.Session()
    sk_login = sk_browser.post(f"{BASE_URL}/login", allow_redirects=False, data={
        "login": sk_phone, "password": "Web-pass2", "next": "/app/items",
    })
    check("storekeeper logs into the web UI",
          sk_login.status_code == 303 and "myequip_session" in sk_browser.cookies,
          sk_login.status_code)
    sk_page = sk_browser.get(f"{BASE_URL}/app/items")
    expect("storekeeper sees the equipment page", sk_page, 200)
    check("storekeeper sees the club equipment", "Веб-рюкзак" in sk_page.text)

    logout = browser.post(f"{BASE_URL}/logout", allow_redirects=False)
    check("logout clears the session",
          logout.status_code == 303 and "myequip_session" not in browser.cookies,
          logout.status_code)
    after_logout = browser.get(f"{BASE_URL}/app/items", allow_redirects=False)
    check("after logout the page redirects to /login",
          after_logout.status_code == 303 and "/login" in after_logout.headers.get("location", ""),
          after_logout.status_code)

    print()
    if FAILURES:
        print(f"RESULT: {len(FAILURES)} FAILED -> {FAILURES}")
        return 1
    print("RESULT: ALL CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
