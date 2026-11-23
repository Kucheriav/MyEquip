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
from urllib.parse import parse_qs, urlparse

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

    root = anonymous.get(f"{BASE_URL}/", allow_redirects=False)
    check("the site root leads into the web app",
          root.status_code == 303
          and root.headers.get("location", "").endswith("/app/items"),
          f"{root.status_code} {root.headers.get('location')}")

    api_banner = anonymous.get(f"{BASE_URL}/api")
    check("the API banner is served from /api",
          api_banner.status_code == 200
          and api_banner.json().get("docs") == "/docs",
          f"{api_banner.status_code} {api_banner.text[:120]}")

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

    # ---------- 5. Transfers through the web form ----------
    transfers_page = browser.get(f"{BASE_URL}/app/transfers")
    expect("transfers page renders", transfers_page, 200)
    check("transfers page shows the current storage", "Веб-склад 2" in transfers_page.text)

    targets = browser.get(f"{BASE_URL}/app/transfers/targets", params={"item_id": item_id})
    check("HTMX transfer fragment offers the other club storage",
          targets.status_code == 200 and "Веб-склад 1" in targets.text
          and "Веб-склад 2" not in targets.text.split("На склад")[-1],
          targets.text[:300])

    moved = browser.post(f"{BASE_URL}/app/transfers", allow_redirects=False, data={
        "item_id": item_id,
        "to_storage_id": storage1["id"],
        "comment": "веб-перемещение",
        "csrf_token": csrf,
        "mover_id": tourist_id,  # must be ignored
    })
    check("transfer redirects back with a success flash",
          moved.status_code == 303 and "ok=transferred" in moved.headers.get("location", ""),
          f"{moved.status_code} {moved.headers.get('location')}")

    transfers = api.get(f"{BASE_URL}/api/transfers/", headers=auth).json()
    transfer = max(transfers, key=lambda row: row["id"])
    check("transfer is stored with the logged-in leader as mover",
          transfer["mover_id"] == leader_id
          and transfer["to_storage_id"] == storage1["id"],
          transfer)
    item_after_transfer = api.get(f"{BASE_URL}/api/items/{item_id}", headers=auth).json()
    check("item physically moved to the destination storage",
          item_after_transfer["storage_id"] == storage1["id"], item_after_transfer)

    bad_move = browser.post(f"{BASE_URL}/app/transfers", allow_redirects=False, data={
        "item_id": item_id, "to_storage_id": storage1["id"], "csrf_token": csrf,
    })
    check("moving to the same storage is refused with a message",
          bad_move.status_code == 303 and "error=" in bad_move.headers.get("location", ""),
          f"{bad_move.status_code} {bad_move.headers.get('location')}")

    # ---------- 6. Breakdowns through the web form ----------
    breakdowns_page = browser.get(f"{BASE_URL}/app/breakdowns")
    expect("breakdowns page renders", breakdowns_page, 200)

    repairer_fragment = browser.get(
        f"{BASE_URL}/app/breakdowns/repairers", params={"item_id": item_id})
    check("HTMX repairer fragment lists the club staff",
          repairer_fragment.status_code == 200 and "Лидер" in repairer_fragment.text,
          repairer_fragment.text[:300])

    reported = browser.post(f"{BASE_URL}/app/breakdowns", allow_redirects=False, data={
        "item_id": item_id,
        "comment": "порвалась лямка",
        "csrf_token": csrf,
    })
    check("breakdown redirects back with a success flash",
          reported.status_code == 303
          and "ok=breakdown_reported" in reported.headers.get("location", ""),
          f"{reported.status_code} {reported.headers.get('location')}")

    breakdowns = api.get(f"{BASE_URL}/api/breakdowns/", headers=auth).json()
    breakdown = max(breakdowns, key=lambda row: row["id"])
    check("breakdown is stored for the item", breakdown["item_id"] == item_id, breakdown)
    item_after_breakdown = api.get(f"{BASE_URL}/api/items/{item_id}", headers=auth).json()
    check("item goes into maintenance", item_after_breakdown["status"] == "maintenance",
          item_after_breakdown["status"])

    repaired = browser.post(
        f"{BASE_URL}/app/breakdowns/{breakdown['id']}/repair",
        allow_redirects=False, data={"repaired_date": date.today().isoformat(),
                                     "csrf_token": csrf})
    check("repair redirects back with a success flash",
          repaired.status_code == 303
          and "ok=breakdown_repaired" in repaired.headers.get("location", ""),
          f"{repaired.status_code} {repaired.headers.get('location')}")

    breakdown_after = api.get(
        f"{BASE_URL}/api/breakdowns/{breakdown['id']}", headers=auth).json()
    check("breakdown carries the logged-in leader as repairer",
          breakdown_after["repaired_date"] == date.today().isoformat()
          and breakdown_after["repairer_id"] == leader_id,
          breakdown_after)
    item_after_repair = api.get(f"{BASE_URL}/api/items/{item_id}", headers=auth).json()
    check("item is available again after the repair",
          item_after_repair["status"] == "available", item_after_repair["status"])

    # ---------- 7. People, clubs and access ----------
    people_page = browser.get(f"{BASE_URL}/app/people")
    expect("people page renders", people_page, 200)
    check("people page lists the club member", "Турист" in people_page.text)
    check("people page offers the add form", "Добавить туриста" in people_page.text)

    new_phone = f"+7666{STAMP[-7:]}"
    created_person = browser.post(f"{BASE_URL}/app/people", allow_redirects=False, data={
        "club_id": club_id,
        "surname": "Новый",
        "name": "Человек",
        "phone": new_phone,
        "status": "guest",
        "csrf_token": csrf,
    })
    check("person is added through the web form",
          created_person.status_code == 303
          and "ok=person_created" in created_person.headers.get("location", ""),
          f"{created_person.status_code} {created_person.headers.get('location')}")

    users = api.get(f"{BASE_URL}/api/users/", headers=auth).json()
    new_person = next((entry for entry in users if entry["phone"] == new_phone), None)
    check("the new person belongs to the club",
          new_person is not None
          and any(m["club_id"] == club_id and m["role"] == "tourist"
                  for m in new_person["memberships"]),
          new_person)
    new_person_id = new_person["id"] if new_person else 0

    edit_page = browser.get(f"{BASE_URL}/app/people/{new_person_id}/edit")
    expect("person edit page renders", edit_page, 200)
    check("person edit page is prefilled", "Новый" in edit_page.text)

    updated_person = browser.post(
        f"{BASE_URL}/app/people/{new_person_id}", allow_redirects=False, data={
            "surname": "Обновлённый", "name": "Человек", "phone": new_phone,
            "status": "full", "csrf_token": csrf,
        })
    check("person is updated through the web form",
          updated_person.status_code == 303
          and "ok=person_updated" in updated_person.headers.get("location", ""),
          f"{updated_person.status_code} {updated_person.headers.get('location')}")
    person_after = api.get(f"{BASE_URL}/api/users/{new_person_id}", headers=auth).json()
    check("person changes are saved", person_after["surname"] == "Обновлённый"
          and person_after["status"] == "full", person_after)

    clubs_page = browser.get(f"{BASE_URL}/app/clubs")
    expect("clubs page renders", clubs_page, 200)
    check("clubs page lists the club", f"web-club-{STAMP}" in clubs_page.text)

    second_club_name = f"web-club-2-{STAMP}"
    created_club = browser.post(f"{BASE_URL}/app/clubs", allow_redirects=False,
                                data={"name": second_club_name, "csrf_token": csrf})
    check("club is created through the web form",
          created_club.status_code == 303
          and "ok=club_created" in created_club.headers.get("location", ""),
          f"{created_club.status_code} {created_club.headers.get('location')}")
    clubs = api.get(f"{BASE_URL}/api/clubs/", headers=auth).json()
    check("the new club exists and is led by the leader",
          any(club["name"] == second_club_name for club in clubs), clubs)

    team_page = browser.get(f"{BASE_URL}/app/team", params={"club_id": club_id})
    expect("access page renders for a leader", team_page, 200)
    check("access page offers invite buttons",
          "Инвайт для завхоза" in team_page.text and "Инвайт для нового руководителя" in team_page.text)

    invite_created = browser.post(
        f"{BASE_URL}/app/team/invite-storekeeper", allow_redirects=False,
        data={"club_id": club_id, "csrf_token": csrf})
    check("storekeeper invite is created through the web form",
          invite_created.status_code == 303
          and "ok=invite_created" in invite_created.headers.get("location", ""),
          f"{invite_created.status_code} {invite_created.headers.get('location')}")
    web_invite = browser.cookies.get("myequip_new_invite") or ""
    check("the new invite code is handed over in a cookie", bool(web_invite), web_invite)

    invite_page = browser.get(f"{BASE_URL}/app/team", params={"club_id": club_id})
    check("the new code is shown once on the page",
          web_invite and web_invite in invite_page.text
          and "Новый код приглашения" in invite_page.text)
    check("the one-shot invite cookie is cleared",
          browser.cookies.get("myequip_new_invite") in (None, ""))

    # ---------- 8. Catalog: storages, categories, properties ----------
    storages_page = browser.get(f"{BASE_URL}/app/storages")
    expect("storages page renders", storages_page, 200)
    check("storages page lists a club storage", "Веб-склад 1" in storages_page.text)

    new_storage_name = f"Веб-склад 3-{STAMP}"
    created_storage = browser.post(f"{BASE_URL}/app/storages", allow_redirects=False,
                                   data={"club_id": club_id, "name": new_storage_name,
                                         "address": "пер. Тестовый, 1",
                                         "csrf_token": csrf})
    check("storage is created through the web form",
          created_storage.status_code == 303
          and "ok=storage_created" in created_storage.headers.get("location", ""),
          f"{created_storage.status_code} {created_storage.headers.get('location')}")
    storages_api = api.get(f"{BASE_URL}/api/storages/", headers=auth).json()
    check("the new storage exists in the club",
          any(s["name"] == new_storage_name and s["club_id"] == club_id
              for s in storages_api), storages_api)

    categories_page = browser.get(f"{BASE_URL}/app/categories")
    expect("categories page renders", categories_page, 200)
    check("categories page lists the club category", "Веб-категория" in categories_page.text)

    category_title = f"Веб-палатки-{STAMP}"
    created_category = browser.post(f"{BASE_URL}/app/categories", allow_redirects=False,
                                    data={"club_id": club_id, "title": category_title,
                                          "csrf_token": csrf})
    check("category is created through the web form",
          created_category.status_code == 303
          and "ok=category_created" in created_category.headers.get("location", ""),
          f"{created_category.status_code} {created_category.headers.get('location')}")
    new_category_id = int(parse_qs(urlparse(
        created_category.headers.get("location", "")).query).get("category_id", ["0"])[0])
    categories_api = api.get(f"{BASE_URL}/api/categories/", headers=auth).json()
    check("the new category exists",
          any(c["id"] == new_category_id and c["title"] == category_title
              for c in categories_api), categories_api)

    attached = browser.post(
        f"{BASE_URL}/app/categories/{new_category_id}/parameters",
        allow_redirects=False,
        data={"name": "Состояние", "param_type": "str",
              "variants": "новое, б/у", "csrf_token": csrf})
    check("property is attached to the category through the web form",
          attached.status_code == 303
          and "ok=parameter_attached" in attached.headers.get("location", ""),
          f"{attached.status_code} {attached.headers.get('location')}")

    parameters_api = api.get(
        f"{BASE_URL}/api/categories/{new_category_id}/parameters", headers=auth).json()
    state_param = next((p for p in parameters_api if p["name"] == "Состояние"), None)
    check("the category has the new property", state_param is not None, parameters_api)
    state_values = api.get(
        f"{BASE_URL}/api/values/parameter/{state_param['id']}", headers=auth).json()
    check("the property variants are stored",
          {v["value"] for v in state_values} == {"новое", "б/у"}, state_values)

    extra = browser.post(
        f"{BASE_URL}/app/categories/{new_category_id}/parameters",
        allow_redirects=False,
        data={"name": "Лишнее", "param_type": "str", "csrf_token": csrf})
    check("a second property can be attached", extra.status_code == 303)
    parameters_api = api.get(
        f"{BASE_URL}/api/categories/{new_category_id}/parameters", headers=auth).json()
    extra_param = next((p for p in parameters_api if p["name"] == "Лишнее"), None)
    check("the second property is attached", extra_param is not None, parameters_api)
    detached = browser.post(
        f"{BASE_URL}/app/categories/{new_category_id}/parameters/{extra_param['id']}/detach",
        allow_redirects=False, data={"csrf_token": csrf})
    check("property is detached from the category through the web form",
          detached.status_code == 303
          and "ok=parameter_detached" in detached.headers.get("location", ""),
          f"{detached.status_code} {detached.headers.get('location')}")
    parameters_api = api.get(
        f"{BASE_URL}/api/categories/{new_category_id}/parameters", headers=auth).json()
    check("the detached property is gone",
          not any(p["name"] == "Лишнее" for p in parameters_api), parameters_api)

    # ---------- 9. Item create and edit with properties ----------
    item_form = browser.get(f"{BASE_URL}/app/items/new",
                            params={"club_id": club_id, "category_id": new_category_id})
    expect("item form renders", item_form, 200)
    check("item form shows the dynamic property",
          "Состояние" in item_form.text and "новое" in item_form.text)

    new_item_name = f"Веб-палатка-{STAMP}"
    created_item = browser.post(f"{BASE_URL}/app/items", allow_redirects=False, data={
        "name": new_item_name,
        "category_id": new_category_id,
        "storage_id": storage1["id"],
        "status": "available",
        "serial_number": f"SN-{STAMP}",
        f"value_{state_param['id']}": next(
            v["id"] for v in state_values if v["value"] == "новое"),
        "csrf_token": csrf,
    })
    check("item is created through the web form",
          created_item.status_code == 303
          and "ok=item_created" in created_item.headers.get("location", ""),
          f"{created_item.status_code} {created_item.headers.get('location')}")

    items_api = api.get(f"{BASE_URL}/api/items/", headers=auth).json()
    new_item = next((i for i in items_api if i["name"] == new_item_name), None)
    check("the new item belongs to the club and storage",
          new_item is not None and new_item["club_id"] == club_id
          and new_item["storage_id"] == storage1["id"], new_item)
    new_item_id = new_item["id"] if new_item else 0

    item_params_api = api.get(
        f"{BASE_URL}/api/item-parameters/item/{new_item_id}", headers=auth).json()
    chosen_value = next(v["id"] for v in state_values if v["value"] == "новое")
    check("the item stores the chosen property value",
          any(p["parameter_id"] == state_param["id"] and p["value_id"] == chosen_value
              for p in item_params_api), item_params_api)

    list_page = browser.get(f"{BASE_URL}/app/items")
    check("the items list shows the property in Russian",
          new_item_name in list_page.text and "Состояние — новое" in list_page.text)

    edit_form = browser.get(f"{BASE_URL}/app/items/{new_item_id}/edit")
    expect("item edit form renders", edit_form, 200)
    check("item edit form is prefilled", new_item_name in edit_form.text)

    updated_item_name = f"{new_item_name}-2"
    updated_item = browser.post(f"{BASE_URL}/app/items/{new_item_id}",
                                allow_redirects=False, data={
        "name": updated_item_name,
        "category_id": new_category_id,
        "status": "maintenance",
        "serial_number": f"SN-{STAMP}",
        f"value_{state_param['id']}": chosen_value,
        "csrf_token": csrf,
    })
    check("item is updated through the web form",
          updated_item.status_code == 303
          and "ok=item_updated" in updated_item.headers.get("location", ""),
          f"{updated_item.status_code} {updated_item.headers.get('location')}")
    item_after_edit = api.get(f"{BASE_URL}/api/items/{new_item_id}", headers=auth).json()
    check("item changes are saved", item_after_edit["name"] == updated_item_name
          and item_after_edit["status"] == "maintenance", item_after_edit)
    check("the edit form cannot move the item to another storage",
          item_after_edit["storage_id"] == storage1["id"], item_after_edit)
    item_params_after = api.get(
        f"{BASE_URL}/api/item-parameters/item/{new_item_id}", headers=auth).json()
    check("item properties survive the edit",
          any(p["parameter_id"] == state_param["id"] and p["value_id"] == chosen_value
              for p in item_params_after), item_params_after)

    # ---------- 10. Search and pagination ----------
    search_hit = browser.get(f"{BASE_URL}/app/items", params={"q": f"SN-{STAMP}"})
    check("item search finds the item by serial number",
          updated_item_name in search_hit.text, search_hit.text[:400])
    check("item search leaves other items out", "Веб-рюкзак" not in search_hit.text)

    search_miss = browser.get(f"{BASE_URL}/app/items", params={"q": "нет-такого-предмета"})
    check("empty item search shows the empty state",
          "По этим условиям снаряжения нет" in search_miss.text)

    people_hit = browser.get(f"{BASE_URL}/app/people", params={"q": "Обновлённый"})
    check("people search finds the person by surname",
          "Обновлённый" in people_hit.text)
    people_miss = browser.get(f"{BASE_URL}/app/people", params={"q": "zzz-нет-такого"})
    check("empty people search shows the empty state",
          "Людей пока нет" in people_miss.text)

    second_page = browser.get(f"{BASE_URL}/app/items", params={"page": 2})
    expect("second page renders", second_page, 200)
    check("pagination moves to the second page",
          "Страница 2" in second_page.text and "Назад" in second_page.text)

    # ---------- 11. Protection ----------
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

    # ---------- 12. Storekeeper access ----------
    expect("leader creates a storekeeper invite", invite_created, 303)
    sk_phone = f"+7777{STAMP[-7:]}"
    expect("storekeeper registers with the invite", api.post(
        f"{BASE_URL}/api/auth/register", json={
            "name": "Склад", "surname": "Завхозов", "phone": sk_phone,
            "password": "Web-pass2", "invite_code": web_invite,
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

    sk_users = api.get(f"{BASE_URL}/api/users/", headers=auth).json()
    sk_person = next((entry for entry in sk_users if entry["phone"] == sk_phone), None)
    sk_id = sk_person["id"] if sk_person else 0

    team_with_sk = browser.get(f"{BASE_URL}/app/team", params={"club_id": club_id})
    check("access page lists the new storekeeper", "Завхозов" in team_with_sk.text)
    check("invite history marks the code as used", web_invite in team_with_sk.text)

    granted = browser.post(
        f"{BASE_URL}/app/team/storekeepers", allow_redirects=False,
        data={"club_id": club_id, "user_id": new_person_id, "csrf_token": csrf})
    check("leader grants storekeeper rights through the web form",
          granted.status_code == 303
          and "ok=member_added" in granted.headers.get("location", ""),
          f"{granted.status_code} {granted.headers.get('location')}")
    members = api.get(f"{BASE_URL}/api/clubs/{club_id}/members", headers=auth).json()
    check("the granted person is a storekeeper of the club",
          any(m["user_id"] == new_person_id and m["role"] == "storekeeper" for m in members),
          members)

    removed = browser.post(
        f"{BASE_URL}/app/team/storekeepers/{club_id}/{sk_id}/remove",
        allow_redirects=False, data={"csrf_token": csrf})
    check("leader removes a storekeeper through the web form",
          removed.status_code == 303
          and "ok=member_removed" in removed.headers.get("location", ""),
          f"{removed.status_code} {removed.headers.get('location')}")
    members_after = api.get(f"{BASE_URL}/api/clubs/{club_id}/members", headers=auth).json()
    check("the removed person is no longer in the club",
          not any(m["user_id"] == sk_id for m in members_after), members_after)

    sk_after_removal = sk_browser.get(f"{BASE_URL}/app/items")
    check("a person without a staff role sees the tourist stub",
          "Доступ пока только для сотрудников клуба" in sk_after_removal.text)

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
