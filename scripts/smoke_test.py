"""
Smoke test for the MyEquip API (authenticated mode).

Checks auth + invite codes + the full domain workflow against a running
server (default http://127.0.0.1:8000):

    invite code bootstrap file -> register leader -> login
    -> new invites -> tourist upgrade by phone match
    -> club -> storages -> users -> category -> parameter -> value
    -> item -> issue/return -> breakdown/repair -> transfer

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
    return response.json()


def expect(name, condition, detail=""):
    if condition:
        print(f"PASS  {name}")
    else:
        print(f"FAIL  {name} {detail}")
        failures.append(name)


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
        "name": "X", "surname": "Y", "phone": "+70000000000",
        "password": "pw123456", "invite_code": "DEADBEEF",
    }),
    400,
)

# ============ 2. First leader registers with the bootstrap code ============
leader = check(
    "first leader registers with bootstrap code",
    requests.post(f"{BASE_URL}/auth/register", json={
        "name": "Анна", "surname": "Руководительева",
        "phone": f"+7900{stamp[-7:]}", "email": f"anna-{stamp}@example.com",
        "password": "Leader-pass1", "invite_code": first_code,
    }),
    201,
)
expect("first leader status is 'full'", leader and leader["status"] == "full", leader)

login = check(
    "first leader logs in",
    requests.post(f"{BASE_URL}/auth/login", json={
        "login": f"+7900{stamp[-7:]}", "password": "Leader-pass1",
    }),
    200,
)
token = login["access_token"] if login else ""
auth = {"Authorization": f"Bearer {token}"}

check(
    "bootstrap code is single-use",
    requests.post(f"{BASE_URL}/auth/register", json={
        "name": "X", "surname": "Y", "phone": "+79990000001",
        "password": "pw123456", "invite_code": first_code,
    }),
    400,
)

# ============ 3. Leader generates new invite codes ============
invite2 = check("leader creates invite #2", requests.post(f"{BASE_URL}/invites/", json={}, headers=auth), 201)
code2 = invite2["code"] if invite2 else ""
check("leader lists invites", requests.get(f"{BASE_URL}/invites/", headers=auth))
check("anonymous cannot create invites", requests.post(f"{BASE_URL}/invites/", json={}), 403)

# ============ 4. Tourist upgrade by phone match (history preserved) ============
tourist_phone = f"+7903{stamp[-7:]}"
tourist = check(
    "leader records a tourist (no password)",
    requests.post(f"{BASE_URL}/users/", headers=auth, json={
        "name": "Борис", "surname": "Туристов", "last_name": None,
        "email": None, "phone": tourist_phone,
        "pswd_hash": None,
        "status": "guest",
    }),
    201,
)
tourist_id = tourist["id"] if tourist else None
upgraded = check(
    "tourist registers with same phone + invite",
    requests.post(f"{BASE_URL}/auth/register", json={
        "name": "Борис", "surname": "Туристов", "phone": tourist_phone,
        "email": f"boris-new-{stamp}@example.com",
        "password": "Tourist-pass1", "invite_code": code2,
    }),
    201,
)
expect(
    "upgrade keeps the same user id (history preserved)",
    upgraded and upgraded["id"] == tourist_id,
    f"tourist_id={tourist_id}, upgraded_id={upgraded and upgraded['id']}",
)
expect("upgraded user status is 'full'", upgraded and upgraded["status"] == "full")
check(
    "upgraded tourist logs in by phone",
    requests.post(f"{BASE_URL}/auth/login", json={
        "login": tourist_phone, "password": "Tourist-pass1",
    }),
    200,
)

# Legacy record (client-side sha256 hash from old GUI) is also upgradeable
legacy_phone = f"+7904{stamp[-7:]}"
legacy = check(
    "leader records a tourist (legacy sha256 hash)",
    requests.post(f"{BASE_URL}/users/", headers=auth, json={
        "name": "Вера", "surname": "Легаси", "last_name": None,
        "email": f"vera-{stamp}@example.com", "phone": legacy_phone,
        "pswd_hash": hashlib.sha256("legacy".encode()).hexdigest(),
        "status": "guest",
    }),
    201,
)
legacy_id = legacy["id"] if legacy else None
invite3 = check("leader creates invite #3", requests.post(f"{BASE_URL}/invites/", json={}, headers=auth), 201)
upgraded2 = check(
    "legacy tourist registers with same phone + invite",
    requests.post(f"{BASE_URL}/auth/register", json={
        "name": "Вера", "surname": "Легаси", "phone": legacy_phone,
        "email": f"vera-new-{stamp}@example.com",
        "password": "Legacy-pass1", "invite_code": invite3["code"] if invite3 else "",
    }),
    201,
)
expect(
    "legacy upgrade keeps the same user id",
    upgraded2 and upgraded2["id"] == legacy_id,
    f"legacy_id={legacy_id}, upgraded_id={upgraded2 and upgraded2['id']}",
)

# A real (bcrypt) account cannot be re-registered on the same phone
hijack = requests.post(f"{BASE_URL}/auth/register", json={
    "name": "Злодей", "surname": "Похититель", "phone": tourist_phone,
    "password": "Hijack-pass1", "invite_code": (invite3 or {}).get("code", ""),
})
if hijack.status_code == 400:
    print("PASS  re-registration on a protected phone rejected with 400")
else:
    print(f"FAIL  phone hijack attempt: {hijack.status_code} (expected 400)")
    failures.append("protected phone hijack")

# ============ 5. Domain workflow (authenticated) ============
# 5.1 Club
club = check("create club", requests.post(f"{BASE_URL}/clubs/", headers=auth, json={"name": f"test-club-{stamp}"}), 201)
club_id = club["id"]

# 5.2 Storages
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

# 5.3 Users (giver / getter, GUI-style records with client sha256 hash)
pswd_hash = hashlib.sha256("test-password".encode()).hexdigest()
user = check(
    "create user (giver)",
    requests.post(f"{BASE_URL}/users/", headers=auth, json={
        "name": "Иван", "surname": "Тестов", "last_name": None,
        "email": f"ivan-{stamp}@example.com", "phone": f"+7901{stamp[-7:]}",
        "pswd_hash": pswd_hash, "status": "full",
    }),
    201,
)
user_id = user["id"]
user2 = check(
    "create user (getter)",
    requests.post(f"{BASE_URL}/users/", headers=auth, json={
        "name": "Мария", "surname": "Петрова", "last_name": None,
        "email": f"maria-{stamp}@example.com", "phone": f"+7902{stamp[-7:]}",
        "pswd_hash": pswd_hash, "status": "full",
    }),
    201,
)
user2_id = user2["id"]

# 5.4 Category (tree root)
category = check(
    "create category",
    requests.post(f"{BASE_URL}/categories/", headers=auth, json={
        "title": "Палатки", "club_id": club_id, "parent_id": None,
    }),
    201,
)
category_id = category["id"]

# 5.5 Parameter + predefined values
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
    requests.post(f"{BASE_URL}/values/", headers=auth, json={"value": "4", "parameter_id": parameter_id}),
    201,
)
value_id = value["id"]

# 5.6 Item
item = check(
    "create item",
    requests.post(f"{BASE_URL}/items/", headers=auth, json={
        "name": "Палатка North Face", "category_id": category_id,
        "storage_id": storage_id, "owner_id": user_id,
        "status": "available", "serial_number": f"SN-{stamp}",
    }),
    201,
)
item_id = item["id"]

# 5.7 Item parameter value
check(
    "attach parameter to item",
    requests.post(f"{BASE_URL}/item-parameters/", headers=auth, json={
        "item_id": item_id, "parameter_id": parameter_id,
        "value_id": value_id, "custom_value": None,
    }),
    201,
)

# 5.8 Distribution: issue
distribution = check(
    "issue item",
    requests.post(f"{BASE_URL}/distributions/", headers=auth, json={
        "item_id": item_id, "giver_id": user_id, "getter_id": user2_id,
        "date": today.isoformat(),
        "expiration_date": (today + timedelta(days=14)).isoformat(),
        "status": "issued", "comment": "на поход выходного дня",
    }),
    201,
)
distribution_id = distribution["id"]
issued_item = requests.get(f"{BASE_URL}/items/{item_id}", headers=auth).json()
expect("item status is 'issued' after issue", issued_item["status"] == "issued", issued_item["status"])

double_issue = requests.post(f"{BASE_URL}/distributions/", headers=auth, json={
    "item_id": item_id, "giver_id": user_id, "getter_id": user2_id,
    "date": today.isoformat(), "status": "issued",
})
expect("double issue rejected with 400", double_issue.status_code == 400, double_issue.status_code)

# 5.9 Return
check(
    "return item (POST /return)",
    requests.post(f"{BASE_URL}/distributions/{distribution_id}/return", headers=auth, json={
        "accepter_id": user_id, "accepting_date": today.isoformat(),
    }),
    200,
)
returned_item = requests.get(f"{BASE_URL}/items/{item_id}", headers=auth).json()
expect("item status is 'available' after return", returned_item["status"] == "available", returned_item["status"])

double_return = requests.post(f"{BASE_URL}/distributions/{distribution_id}/return", headers=auth, json={})
expect("double return rejected with 400", double_return.status_code == 400, double_return.status_code)

# 5.10 Breakdown
breakdown = check(
    "report breakdown",
    requests.post(f"{BASE_URL}/breakdowns/", headers=auth, json={
        "item_id": item_id, "comment": "сломана дуга",
        "date": today.isoformat(), "repairer_id": None,
    }),
    201,
)
breakdown_id = breakdown["id"]
maintenance_item = requests.get(f"{BASE_URL}/items/{item_id}", headers=auth).json()
expect("item status is 'maintenance' after breakdown", maintenance_item["status"] == "maintenance", maintenance_item["status"])

check(
    "mark repaired (POST /repair)",
    requests.post(f"{BASE_URL}/breakdowns/{breakdown_id}/repair", headers=auth, json={
        "repairer_id": user_id, "repaired_date": today.isoformat(),
    }),
    200,
)
repaired_item = requests.get(f"{BASE_URL}/items/{item_id}", headers=auth).json()
expect("item status is 'available' after repair", repaired_item["status"] == "available", repaired_item["status"])

# 5.11 Transfer between storages
transfer = check(
    "transfer item to storage2",
    requests.post(f"{BASE_URL}/transfers/", headers=auth, json={
        "item_id": item_id, "from_storage_id": storage_id, "to_storage_id": storage2_id,
        "date": today.isoformat(), "mover_id": user_id,
        "comment": "передали на другой склад",
    }),
    201,
)
moved_item = requests.get(f"{BASE_URL}/items/{item_id}", headers=auth).json()
expect(
    "item storage updated after transfer",
    moved_item["storage_id"] == storage2_id,
    f"got {moved_item['storage_id']}, expected {storage2_id}",
)
bad_transfer = requests.post(f"{BASE_URL}/transfers/", headers=auth, json={
    "item_id": item_id, "from_storage_id": storage_id, "to_storage_id": storage2_id,
    "date": today.isoformat(),
})
expect("transfer from wrong source rejected with 400", bad_transfer.status_code == 400, bad_transfer.status_code)
check("transfer history", requests.get(f"{BASE_URL}/transfers/item/{item_id}", headers=auth))

# ============ 6. Access control & misc ============
check("anonymous read rejected with 401", requests.get(f"{BASE_URL}/clubs"), 401)
check("wrong password rejected with 401", requests.post(f"{BASE_URL}/auth/login", json={
    "login": f"+7900{stamp[-7:]}", "password": "wrong",
}), 401)
check("/health", requests.get(BASE_URL.replace("/api", "") + "/health"))

print()
if failures:
    print(f"RESULT: {len(failures)} FAILED: {failures}")
    sys.exit(1)
print("RESULT: ALL CHECKS PASSED")
