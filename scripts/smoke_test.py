"""
Smoke test for the MyEquip API (authenticated mode, role model).

Checks auth + typed invites + roles + club isolation + the domain workflow
against a running server (default http://127.0.0.1:8000):

    bootstrap invite -> first leader -> club/storages
    -> leader invite -> tourist upgrade (same id)
    -> storekeeper invite -> storekeeper registration
    -> storekeeper may work with items but not manage the club
    -> foreign leader sees nothing
    -> issue/return -> breakdown/repair -> transfer
    -> leader grants the storekeeper a second club

Usage:
    python scripts/smoke_test.py            # against 127.0.0.1:8000
    python scripts/smoke_test.py BASE_URL   # custom base URL
"""
import hashlib
import os
import sys
from datetime import date, datetime, timedelta

import requests

BASE_URL = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000") + "/api"

# The first leader invite code is written here by the server bootstrap
INVITE_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "invite_code.txt")

today = date.today()
stamp = datetime.now().strftime("%Y%m%d%H%M%S%f")  # unique suffix per run

failures = []


def check(name, response, expected_status=200):
    ok = response.status_code == expected_status
    print(f"{'PASS' if ok else 'FAIL'}  {name}: {response.status_code} (expected {expected_status})")
    if not ok:
        failures.append(name)
        try:
            print("      ->", response.json())
        except Exception:
            print("      ->", response.text[:200])
        return None
    if response.status_code == 204 or not response.content:
        return True
    return response.json()


def expect(name, condition, detail=""):
    if condition:
        print(f"PASS  {name}")
    else:
        print(f"FAIL  {name} {detail}")
        failures.append(name)


def register(phone, invite_code, name="Тест", surname="Тестов", password="pw123456", email=None):
    return requests.post(f"{BASE_URL}/auth/register", json={
        "name": name, "surname": surname, "phone": phone,
        "email": email, "password": password, "invite_code": invite_code,
    })


def login(login_value, password):
    return requests.post(f"{BASE_URL}/auth/login", json={
        "login": login_value, "password": password,
    })


# ============ 0. Invite bootstrap ============
if not os.path.exists(INVITE_FILE):
    print(f"FAIL  invite_code.txt not found at {INVITE_FILE}")
    sys.exit(1)
first_code = None
for line in open(INVITE_FILE, encoding="utf-8"):
    line = line.strip()
    if len(line) == 8 and line.isalnum():
        first_code = line
        break
expect("invite code found in invite_code.txt", bool(first_code), first_code or "")

# ============ 1. Registration is impossible without / with a bad code ============
check(
    "register without invite code rejected",
    requests.post(f"{BASE_URL}/auth/register", json={
        "name": "X", "surname": "Y", "phone": "+70000000000",
        "password": "pw123456", "invite_code": "",
    }),
    400,
)
check(
    "register with wrong invite code rejected",
    requests.post(f"{BASE_URL}/auth/register", json={
        "name": "X", "surname": "Y", "phone": "+70000000001",
        "password": "pw123456", "invite_code": "DEADBEEF",
    }),
    400,
)

# ============ 2. First leader registers with the bootstrap code ============
leader_phone = f"+7900{stamp[-7:]}"
leader = check(
    "first leader registers with bootstrap code",
    register(leader_phone, first_code, name="Анна", surname="Руководительева",
             password="Leader-pass1", email=f"anna-{stamp}@example.com"),
    201,
)
expect("first leader status is 'full'", leader and leader["status"] == "full", leader)
expect("first leader role is 'leader'", leader and leader["role"] == "leader", leader)
expect("first leader starts without clubs", leader and leader["club_ids"] == [], leader)

check(
    "first leader logs in",
    login(leader_phone, "Leader-pass1"),
)
login_resp = login(leader_phone, "Leader-pass1")
token = login_resp.json()["access_token"] if login_resp.status_code == 200 else ""
auth = {"Authorization": f"Bearer {token}"}

me = check("GET /auth/me", requests.get(f"{BASE_URL}/auth/me", headers=auth))
expect("me reports leader role", me and me["role"] == "leader", me)

check(
    "bootstrap code is single-use",
    register("+79990000001", first_code),
    400,
)

# ============ 3. Leader creates a club and storages ============
club = check("create club", requests.post(
    f"{BASE_URL}/clubs/", headers=auth, json={"name": f"test-club-{stamp}"}), 201)
club_id = club["id"]

me = requests.get(f"{BASE_URL}/auth/me", headers=auth).json()
expect("leader is a member of the created club", club_id in me["club_ids"], me)

storage = check(
    "create storage",
    requests.post(f"{BASE_URL}/storages/", headers=auth, json={
        "name": f"test-storage-{stamp}", "address": "ул. Лесная, 1", "club_id": club_id,
    }),
    201,
)
storage_id = storage["id"]
storage2 = check(
    "create second storage",
    requests.post(f"{BASE_URL}/storages/", headers=auth, json={
        "name": f"test-storage2-{stamp}", "address": "ул. Горная, 2", "club_id": club_id,
    }),
    201,
)
storage2_id = storage2["id"]

# ============ 4. Leader generates typed invite codes ============
invite_leader2 = check(
    "leader creates an independent-leader invite",
    requests.post(f"{BASE_URL}/invites/", headers=auth, json={"role": "leader"}), 201,
)
invite_sk = check(
    "leader creates a storekeeper invite for their club",
    requests.post(f"{BASE_URL}/invites/", headers=auth, json={
        "role": "storekeeper", "club_id": club_id}), 201,
)
expect("storekeeper invite carries the club",
       invite_sk and invite_sk["club_id"] == club_id, invite_sk)

check(
    "storekeeper invite without a club rejected",
    requests.post(f"{BASE_URL}/invites/", headers=auth, json={"role": "storekeeper"}),
    400,
)
check("leader lists their invites", requests.get(f"{BASE_URL}/invites/", headers=auth))
check("anonymous cannot create invites", requests.post(
    f"{BASE_URL}/invites/", json={"role": "leader"}), 401)

# ============ 5. Tourist upgrade by phone match (history preserved) ============
tourist_phone = f"+7903{stamp[-7:]}"
tourist = check(
    "leader records a tourist in the club",
    requests.post(f"{BASE_URL}/users/", headers=auth, json={
        "club_id": club_id,
        "name": "Борис", "surname": "Туристов", "last_name": None,
        "email": None, "phone": tourist_phone,
        "pswd_hash": None, "status": "guest",
    }),
    201,
)
tourist_id = tourist["id"] if tourist else None
expect("tourist is a club member", tourist and club_id in tourist["club_ids"], tourist)

check(
    "tourist creation without a club rejected",
    requests.post(f"{BASE_URL}/users/", headers=auth, json={
        "name": "Без", "surname": "Клуба", "phone": f"+7908{stamp[-7:]}",
        "pswd_hash": None, "status": "guest",
    }),
    400,
)

upgraded = check(
    "tourist registers with same phone + leader invite",
    register(tourist_phone, invite_leader2["code"],
             name="Борис", surname="Туристов",
             password="Tourist-pass1", email=f"boris-new-{stamp}@example.com"),
    201,
)
expect("upgrade keeps the same user id (history preserved)",
       upgraded and upgraded["id"] == tourist_id,
       f"tourist_id={tourist_id}, upgraded_id={upgraded and upgraded['id']}")
expect("upgraded user becomes a leader", upgraded and upgraded["role"] == "leader")
expect("upgraded leader keeps the old membership",
       upgraded and club_id in upgraded["club_ids"], upgraded)
check(
    "upgraded tourist logs in by phone",
    login(tourist_phone, "Tourist-pass1"),
)

# Legacy record (client-side sha256 hash from old GUI) is also upgradeable
legacy_phone = f"+7904{stamp[-7:]}"
legacy = check(
    "leader records a tourist (legacy sha256 hash)",
    requests.post(f"{BASE_URL}/users/", headers=auth, json={
        "club_id": club_id,
        "name": "Вера", "surname": "Легаси", "last_name": None,
        "email": f"vera-{stamp}@example.com", "phone": legacy_phone,
        "pswd_hash": hashlib.sha256("legacy".encode()).hexdigest(),
        "status": "guest",
    }),
    201,
)
legacy_id = legacy["id"] if legacy else None
invite3 = check("leader creates another leader invite", requests.post(
    f"{BASE_URL}/invites/", headers=auth, json={"role": "leader"}), 201)
upgraded2 = check(
    "legacy tourist registers with same phone + invite",
    register(legacy_phone, invite3["code"], name="Вера", surname="Легаси",
             password="Legacy-pass1", email=f"vera-new-{stamp}@example.com"),
    201,
)
expect("legacy upgrade keeps the same user id",
       upgraded2 and upgraded2["id"] == legacy_id,
       f"legacy_id={legacy_id}, upgraded_id={upgraded2 and upgraded2['id']}")

# A real (bcrypt) account cannot be re-registered on the same phone
invite4 = check("leader creates one more leader invite", requests.post(
    f"{BASE_URL}/invites/", headers=auth, json={"role": "leader"}), 201)
hijack = register(tourist_phone, invite4["code"], name="Злодей", surname="Похититель",
                  password="Hijack-pass1")
expect("re-registration on a protected phone rejected with 400",
       hijack.status_code == 400, hijack.status_code)

# Two tourists without email must both be creatable
check(
    "leader records tourist #1 without email",
    requests.post(f"{BASE_URL}/users/", headers=auth, json={
        "club_id": club_id,
        "name": "Без", "surname": "Почты-1", "phone": f"+7905{stamp[-7:]}",
        "email": None, "status": "guest",
    }),
    201,
)
no_email_2 = requests.post(f"{BASE_URL}/users/", headers=auth, json={
    "club_id": club_id,
    "name": "Без", "surname": "Почты-2", "phone": f"+7906{stamp[-7:]}",
    "email": None, "status": "guest",
})
expect("leader records tourist #2 without email (no false duplicate)",
       no_email_2.status_code == 201, no_email_2.status_code)

dup_email = requests.post(f"{BASE_URL}/users/", headers=auth, json={
    "club_id": club_id,
    "name": "Дубль", "surname": "Почты", "phone": f"+7907{stamp[-7:]}",
    "email": f"boris-new-{stamp}@example.com", "status": "guest",
})
expect("duplicate email rejected with 400", dup_email.status_code == 400, dup_email.status_code)

dup_phone = requests.post(f"{BASE_URL}/users/", headers=auth, json={
    "club_id": club_id,
    "name": "Дубль", "surname": "Телефона", "phone": f"+7905{stamp[-7:]}",
    "email": None, "status": "guest",
})
expect("duplicate phone rejected with readable 400", dup_phone.status_code == 400, dup_phone.status_code)

# ============ 6. Storekeeper registration and permissions ============
sk_phone = f"+7910{stamp[-7:]}"
storekeeper = check(
    "storekeeper registers with the storekeeper invite",
    register(sk_phone, invite_sk["code"], name="Степан", surname="Кладовщиков",
             password="Store-pass1", email=f"sk-{stamp}@example.com"),
    201,
)
sk_id = storekeeper["id"] if storekeeper else None
expect("storekeeper role is 'storekeeper'",
       storekeeper and storekeeper["role"] == "storekeeper", storekeeper)
expect("storekeeper belongs only to the invite's club",
       storekeeper and storekeeper["club_ids"] == [club_id], storekeeper)

check("storekeeper logs in", login(sk_phone, "Store-pass1"))
sk_login = login(sk_phone, "Store-pass1")
sk_token = sk_login.json()["access_token"] if sk_login.status_code == 200 else ""
sk_auth = {"Authorization": f"Bearer {sk_token}"}

sk_me = requests.get(f"{BASE_URL}/auth/me", headers=sk_auth).json()
expect("storekeeper /auth/me reports role and club",
       sk_me.get("role") == "storekeeper" and sk_me.get("club_ids") == [club_id], sk_me)

check("storekeeper cannot create a club", requests.post(
    f"{BASE_URL}/clubs/", headers=sk_auth, json={"name": f"sk-club-{stamp}"}), 403)
check("storekeeper cannot create a storage", requests.post(
    f"{BASE_URL}/storages/", headers=sk_auth, json={
        "name": "sk-storage", "club_id": club_id}), 403)
check("storekeeper cannot create a category", requests.post(
    f"{BASE_URL}/categories/", headers=sk_auth, json={
        "title": "sk-category", "club_id": club_id}), 403)
check("storekeeper cannot create a person", requests.post(
    f"{BASE_URL}/users/", headers=sk_auth, json={
        "club_id": club_id, "name": "Нельзя", "surname": "Создать",
        "phone": f"+7911{stamp[-7:]}", "status": "guest"}), 403)
check("storekeeper cannot create a parameter", requests.post(
    f"{BASE_URL}/parameters/", headers=sk_auth, json={
        "name": f"sk-param-{stamp}", "param_type": "str"}), 403)
check("storekeeper can read people of the club", requests.get(
    f"{BASE_URL}/users/", headers=sk_auth))

# ============ 7. Domain workflow (leader) ============
user = check(
    "create user (giver, member of the club)",
    requests.post(f"{BASE_URL}/users/", headers=auth, json={
        "club_id": club_id,
        "name": "Иван", "surname": "Тестов", "last_name": None,
        "email": f"ivan-{stamp}@example.com", "phone": f"+7901{stamp[-7:]}",
        "pswd_hash": hashlib.sha256("test-password".encode()).hexdigest(),
        "status": "full",
    }),
    201,
)
user_id = user["id"]
user2 = check(
    "create user (getter, member of the club)",
    requests.post(f"{BASE_URL}/users/", headers=auth, json={
        "club_id": club_id,
        "name": "Мария", "surname": "Петрова", "last_name": None,
        "email": f"maria-{stamp}@example.com", "phone": f"+7902{stamp[-7:]}",
        "pswd_hash": hashlib.sha256("test-password".encode()).hexdigest(),
        "status": "full",
    }),
    201,
)
user2_id = user2["id"]

category = check(
    "create category",
    requests.post(f"{BASE_URL}/categories/", headers=auth, json={
        "title": "Палатки", "club_id": club_id, "parent_id": None,
    }),
    201,
)
category_id = category["id"]

parameter = check(
    "create parameter",
    requests.post(f"{BASE_URL}/parameters/", headers=auth, json={
        "name": f"Вместимость-{stamp}", "param_type": "int",
    }),
    201,
)
parameter_id = parameter["id"]
value = check(
    "create value",
    requests.post(f"{BASE_URL}/values/", headers=auth, json={
        "value": "4", "parameter_id": parameter_id}),
    201,
)
value_id = value["id"]

# The item belongs to the club; it has no owner field any more
item = check(
    "create item",
    requests.post(f"{BASE_URL}/items/", headers=auth, json={
        "name": "Палатка North Face", "category_id": category_id,
        "storage_id": storage_id, "status": "available",
        "serial_number": f"SN-{stamp}",
    }),
    201,
)
item_id = item["id"]
expect("item gets the club from its category/storage", item and item["club_id"] == club_id, item)

check(
    "category and storage from different clubs rejected",
    requests.post(f"{BASE_URL}/items/", headers=auth, json={
        "name": "Чужая палатка", "category_id": category_id,
        "storage_id": 999999, "status": "available",
    }),
    404,
)

# ============ 8. Storekeeper equipment operations ============
sk_item = check(
    "storekeeper creates an item",
    requests.post(f"{BASE_URL}/items/", headers=sk_auth, json={
        "name": "Спальник", "category_id": category_id,
        "storage_id": storage_id, "status": "available",
    }),
    201,
)
sk_item_id = sk_item["id"] if sk_item else None

check(
    "storekeeper updates the item",
    requests.put(f"{BASE_URL}/items/{sk_item_id}", headers=sk_auth, json={
        "name": "Спальник тёплый"}),
    200,
)
check(
    "storekeeper cannot delete the item",
    requests.delete(f"{BASE_URL}/items/{sk_item_id}", headers=sk_auth),
    403,
)
check(
    "storekeeper attaches a parameter value to an item",
    requests.post(f"{BASE_URL}/item-parameters/", headers=sk_auth, json={
        "item_id": item_id, "parameter_id": parameter_id,
        "value_id": value_id, "custom_value": None,
    }),
    201,
)
check(
    "storekeeper cannot attach a parameter to a category",
    requests.post(f"{BASE_URL}/categories/{category_id}/parameters", headers=sk_auth,
                  json={"parameter_id": parameter_id}),
    403,
)

# ============ 9. Category parameters: attach, duplicates, inheritance ============
attach_resp = requests.post(
    f"{BASE_URL}/categories/{category_id}/parameters", headers=auth,
    json={"parameter_id": parameter_id},
)
expect("attach parameter to category", attach_resp.status_code == 201, attach_resp.status_code)

dup_attach = requests.post(
    f"{BASE_URL}/categories/{category_id}/parameters", headers=auth,
    json={"parameter_id": parameter_id},
)
expect("double attach rejected with 400", dup_attach.status_code == 400, dup_attach.status_code)

own_params = requests.get(
    f"{BASE_URL}/categories/{category_id}/parameters", headers=auth).json()
expect(
    "own category parameter listed as not inherited",
    any(p["id"] == parameter_id and not p["inherited"] for p in own_params),
    own_params,
)

child_category = check(
    "create child category",
    requests.post(f"{BASE_URL}/categories/", headers=auth, json={
        "title": "Зимние палатки", "club_id": club_id, "parent_id": category_id,
    }),
    201,
)
child_category_id = child_category["id"]

child_params_all = requests.get(
    f"{BASE_URL}/categories/{child_category_id}/parameters?include_inherited=true", headers=auth).json()
expect(
    "child inherits parent's parameter (inherited=True)",
    any(p["id"] == parameter_id and p["inherited"] for p in child_params_all),
    child_params_all,
)
child_params_own = requests.get(
    f"{BASE_URL}/categories/{child_category_id}/parameters?include_inherited=false", headers=auth).json()
expect(
    "child's own-only list excludes inherited parameter",
    all(p["id"] != parameter_id for p in child_params_own),
    child_params_own,
)

child_item = check(
    "create item in child category",
    requests.post(f"{BASE_URL}/items/", headers=auth, json={
        "name": "Зимняя палатка", "category_id": child_category_id,
        "storage_id": storage_id, "status": "available",
    }),
    201,
)
free_value = check(
    "store free-input parameter value on item",
    requests.post(f"{BASE_URL}/item-parameters/", headers=auth, json={
        "item_id": child_item["id"], "parameter_id": parameter_id,
        "value_id": None, "custom_value": "6",
    }),
    201,
)
item_values = requests.get(
    f"{BASE_URL}/item-parameters/item/{child_item['id']}", headers=auth).json()
expect(
    "item parameter value readable back",
    any(v["parameter_id"] == parameter_id and v["custom_value"] == "6" for v in item_values),
    item_values,
)
requests.delete(f"{BASE_URL}/item-parameters/{free_value['id']}", headers=auth)
check("leader deletes an item", requests.delete(
    f"{BASE_URL}/items/{child_item['id']}", headers=auth), 204)

detach_resp = requests.delete(
    f"{BASE_URL}/categories/{category_id}/parameters/{parameter_id}", headers=auth)
expect("detach parameter from category", detach_resp.status_code == 204, detach_resp.status_code)
re_params = requests.get(
    f"{BASE_URL}/categories/{child_category_id}/parameters?include_inherited=true", headers=auth).json()
expect(
    "detached parameter disappears from child's inherited set",
    all(p["id"] != parameter_id for p in re_params),
    re_params,
)

# ============ 10. Distribution: issue by leader, return by storekeeper ============
distribution = check(
    "leader issues the item",
    requests.post(f"{BASE_URL}/distributions/", headers=auth, json={
        "item_id": item_id, "giver_id": user_id, "getter_id": user2_id,
        "date": today.isoformat(),
        "expiration_date": (today + timedelta(days=14)).isoformat(),
        "status": "issued", "comment": "на поход выходного дня",
    }),
    201,
)
distribution_id = distribution["id"]
issued_item = requests.get(f"{BASE_URL}/items/{item_id}", headers=sk_auth).json()
expect("item status is 'issued' after issue", issued_item["status"] == "issued", issued_item["status"])

check(
    "storekeeper cannot issue an unavailable item twice",
    requests.post(f"{BASE_URL}/distributions/", headers=sk_auth, json={
        "item_id": item_id, "giver_id": user_id, "getter_id": user2_id,
        "date": today.isoformat(), "status": "issued",
    }),
    400,
)
check(
    "storekeeper returns the item (POST /return)",
    requests.post(f"{BASE_URL}/distributions/{distribution_id}/return", headers=sk_auth, json={
        "accepter_id": user_id, "accepting_date": today.isoformat(),
    }),
    200,
)
returned_item = requests.get(f"{BASE_URL}/items/{item_id}", headers=sk_auth).json()
expect("item status is 'available' after return",
       returned_item["status"] == "available", returned_item["status"])
check(
    "double return rejected with 400",
    requests.post(f"{BASE_URL}/distributions/{distribution_id}/return", headers=auth, json={}),
    400,
)

# ============ 11. Breakdown (storekeeper) ============
breakdown = check(
    "storekeeper reports a breakdown",
    requests.post(f"{BASE_URL}/breakdowns/", headers=sk_auth, json={
        "item_id": item_id, "comment": "сломана дуга",
        "date": today.isoformat(), "repairer_id": None,
    }),
    201,
)
breakdown_id = breakdown["id"]
maintenance_item = requests.get(f"{BASE_URL}/items/{item_id}", headers=sk_auth).json()
expect("item status is 'maintenance' after breakdown",
       maintenance_item["status"] == "maintenance", maintenance_item["status"])
check(
    "storekeeper marks the item repaired",
    requests.post(f"{BASE_URL}/breakdowns/{breakdown_id}/repair", headers=sk_auth, json={
        "repairer_id": user_id, "repaired_date": today.isoformat(),
    }),
    200,
)
repaired_item = requests.get(f"{BASE_URL}/items/{item_id}", headers=sk_auth).json()
expect("item status is 'available' after repair",
       repaired_item["status"] == "available", repaired_item["status"])

# ============ 12. Transfer between storages of the same club ============
check(
    "storekeeper transfers the item to storage2",
    requests.post(f"{BASE_URL}/transfers/", headers=sk_auth, json={
        "item_id": item_id, "from_storage_id": storage_id, "to_storage_id": storage2_id,
        "date": today.isoformat(), "mover_id": user_id,
        "comment": "передали на другой склад",
    }),
    201,
)
moved_item = requests.get(f"{BASE_URL}/items/{item_id}", headers=sk_auth).json()
expect("item storage updated after transfer",
       moved_item["storage_id"] == storage2_id,
       f"got {moved_item['storage_id']}, expected {storage2_id}")
check(
    "transfer from a wrong source rejected with 400",
    requests.post(f"{BASE_URL}/transfers/", headers=auth, json={
        "item_id": item_id, "from_storage_id": storage_id, "to_storage_id": storage2_id,
        "date": today.isoformat(),
    }),
    400,
)
check("transfer history", requests.get(f"{BASE_URL}/transfers/item/{item_id}", headers=auth))

# ============ 13. Foreign leader sees nothing ============
foreign_phone = f"+7920{stamp[-7:]}"
invite_foreign = check("leader creates an invite for a foreign leader", requests.post(
    f"{BASE_URL}/invites/", headers=auth, json={"role": "leader"}), 201)
foreign = check(
    "foreign leader registers",
    register(foreign_phone, invite_foreign["code"], name="Чужой", surname="Руководитель",
             password="Foreign-pass1", email=f"foreign-{stamp}@example.com"),
    201,
)
foreign_login = login(foreign_phone, "Foreign-pass1")
foreign_token = foreign_login.json()["access_token"] if foreign_login.status_code == 200 else ""
foreign_auth = {"Authorization": f"Bearer {foreign_token}"}

expect("foreign leader sees no clubs",
       requests.get(f"{BASE_URL}/clubs", headers=foreign_auth).json() == [])
expect("foreign leader sees no items",
       requests.get(f"{BASE_URL}/items", headers=foreign_auth).json() == [])
expect("foreign leader sees no people",
       requests.get(f"{BASE_URL}/users", headers=foreign_auth).json() == [])
check("foreign leader cannot read the club", requests.get(
    f"{BASE_URL}/clubs/{club_id}", headers=foreign_auth), 403)
check("foreign leader cannot read the item", requests.get(
    f"{BASE_URL}/items/{item_id}", headers=foreign_auth), 403)
check("foreign leader cannot create a storekeeper invite for a foreign club",
      requests.post(f"{BASE_URL}/invites/", headers=foreign_auth, json={
          "role": "storekeeper", "club_id": club_id}), 403)
check("foreign leader cannot read club members", requests.get(
    f"{BASE_URL}/clubs/{club_id}/members", headers=foreign_auth), 403)

# ============ 14. Leader grants the storekeeper a second club ============
club2 = check("leader creates a second club", requests.post(
    f"{BASE_URL}/clubs/", headers=auth, json={"name": f"test-club2-{stamp}"}), 201)
club2_id = club2["id"]
storage3 = check(
    "create a storage in the second club",
    requests.post(f"{BASE_URL}/storages/", headers=auth, json={
        "name": f"test-storage3-{stamp}", "address": "ул. Степная, 3",
        "club_id": club2_id,
    }),
    201,
)
storage3_id = storage3["id"]

check(
    "storekeeper cannot grant themselves a club",
    requests.post(f"{BASE_URL}/clubs/{club2_id}/members", headers=sk_auth, json={
        "user_id": sk_id, "role": "storekeeper"}),
    403,
)
check(
    "leader grants the storekeeper the second club",
    requests.post(f"{BASE_URL}/clubs/{club2_id}/members", headers=auth, json={
        "user_id": sk_id, "role": "storekeeper"}),
    201,
)
sk_clubs = requests.get(f"{BASE_URL}/clubs", headers=sk_auth).json()
expect("storekeeper now sees both clubs",
       {c["id"] for c in sk_clubs} == {club_id, club2_id}, sk_clubs)
check(
    "transfer to another club's storage rejected with 400",
    requests.post(f"{BASE_URL}/transfers/", headers=sk_auth, json={
        "item_id": item_id, "from_storage_id": storage2_id, "to_storage_id": storage3_id,
        "date": today.isoformat(),
    }),
    400,
)

# ============ 15. Access control & misc ============
check("anonymous read rejected with 401", requests.get(f"{BASE_URL}/clubs"), 401)
check("wrong password rejected with 401", login(leader_phone, "wrong"), 401)
check("/health", requests.get(BASE_URL.replace("/api", "") + "/health"))

print()
if failures:
    print(f"RESULT: {len(failures)} FAILED: {failures}")
    sys.exit(1)
print("RESULT: ALL CHECKS PASSED")
