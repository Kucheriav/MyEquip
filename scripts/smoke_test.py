"""
Smoke test for the MyEquip API.

Checks the full domain workflow against a running server
(default http://127.0.0.1:8000):

    club -> storage -> user -> category -> parameter -> value
    -> item -> item parameter -> distribution (issue/return)
    -> breakdown (report/repair)

Usage:
    python scripts/smoke_test.py            # against 127.0.0.1:8000
    python scripts/smoke_test.py BASE_URL   # custom base URL
"""
import sys
from datetime import date, datetime, timedelta

import requests

BASE_URL = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000") + "/api"

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


# 1. Club
club = check("create club", requests.post(f"{BASE_URL}/clubs/", json={"name": f"test-club-{stamp}"}, ), 201)
club_id = club["id"]

# 2. Storage
storage = check(
    "create storage",
    requests.post(f"{BASE_URL}/storages/", json={"name": f"test-storage-{stamp}", "address": "ул. Лесная, 1", "club_id": club_id}),
    201,
)
storage_id = storage["id"]

# 3. User (giver/owner; password hash is computed by the client in current design)
import hashlib
pswd_hash = hashlib.sha256("test-password".encode()).hexdigest()
user = check(
    "create user (giver)",
    requests.post(f"{BASE_URL}/users/", json={
        "name": "Иван", "surname": "Тестов", "last_name": None,
        "email": f"ivan-{stamp}@example.com", "phone": f"+7900{stamp[-7:]}",
        "pswd_hash": pswd_hash, "status": "full",
    }),
    201,
)
user_id = user["id"]
user2 = check(
    "create user (getter)",
    requests.post(f"{BASE_URL}/users/", json={
        "name": "Мария", "surname": "Петрова", "last_name": None,
        "email": f"maria-{stamp}@example.com", "phone": f"+7901{stamp[-7:]}",
        "pswd_hash": pswd_hash, "status": "full",
    }),
    201,
)
user2_id = user2["id"]

# 4. Category (tree root)
category = check(
    "create category",
    requests.post(f"{BASE_URL}/categories/", json={"title": "Палатки", "club_id": club_id, "parent_id": None}),
    201,
)
category_id = category["id"]

# 5. Parameter + predefined values
parameter = check(
    "create parameter",
    requests.post(f"{BASE_URL}/parameters/", json={"name": f"Вместимость-{stamp}", "param_type": "int"}),
    201,
)
parameter_id = parameter["id"]
value = check(
    "create value",
    requests.post(f"{BASE_URL}/values/", json={"value": "4", "parameter_id": parameter_id}),
    201,
)
value_id = value["id"]

# 6. Item
item = check(
    "create item",
    requests.post(f"{BASE_URL}/items/", json={
        "name": "Палатка Norht Face", "category_id": category_id,
        "storage_id": storage_id, "owner_id": user_id,
        "status": "available", "serial_number": f"SN-{stamp}",
    }),
    201,
)
item_id = item["id"]

# 7. Item parameter value
check(
    "attach parameter to item",
    requests.post(f"{BASE_URL}/item-parameters/", json={
        "item_id": item_id, "parameter_id": parameter_id,
        "value_id": value_id, "custom_value": None,
    }),
    201,
)

# 8. Distribution: issue
distribution = check(
    "issue item",
    requests.post(f"{BASE_URL}/distributions/", json={
        "item_id": item_id, "giver_id": user_id, "getter_id": user2_id,
        "date": today.isoformat(),
        "expiration_date": (today + timedelta(days=14)).isoformat(),
        "status": "issued", "comment": "на поход выходного дня",
    }),
    201,
)
distribution_id = distribution["id"]
check("item status after issue", requests.get(f"{BASE_URL}/items/{item_id}"))  # asserted below
issued_item = requests.get(f"{BASE_URL}/items/{item_id}").json()
if issued_item["status"] == "issued":
    print("PASS  item status is 'issued' after issue")
else:
    print(f"FAIL  item status is '{issued_item['status']}' after issue (expected 'issued')")
    failures.append("item status after issue")

# 8a. Cannot issue the same item twice
double_issue = requests.post(f"{BASE_URL}/distributions/", json={
    "item_id": item_id, "giver_id": user_id, "getter_id": user2_id,
    "date": today.isoformat(), "status": "issued",
})
if double_issue.status_code == 400:
    print("PASS  double issue rejected with 400")
else:
    print(f"FAIL  double issue: {double_issue.status_code} (expected 400)")
    failures.append("double issue")

# 9. Distribution: return via the dedicated endpoint
check(
    "return item (POST /return)",
    requests.post(f"{BASE_URL}/distributions/{distribution_id}/return", json={
        "accepter_id": user_id, "accepting_date": today.isoformat(),
    }),
    200,
)
returned_item = requests.get(f"{BASE_URL}/items/{item_id}").json()
if returned_item["status"] == "available":
    print("PASS  item status is 'available' after return")
else:
    print(f"FAIL  item status is '{returned_item['status']}' after return (expected 'available')")
    failures.append("item status after return")
# 9a. Double return is rejected
double_return = requests.post(f"{BASE_URL}/distributions/{distribution_id}/return", json={})
if double_return.status_code == 400:
    print("PASS  double return rejected with 400")
else:
    print(f"FAIL  double return: {double_return.status_code} (expected 400)")
    failures.append("double return")

# 10. Breakdown: report
breakdown = check(
    "report breakdown",
    requests.post(f"{BASE_URL}/breakdowns/", json={
        "item_id": item_id, "comment": "сломана дуга",
        "date": today.isoformat(), "repairer_id": None,
    }),
    201,
)
breakdown_id = breakdown["id"]
maintenance_item = requests.get(f"{BASE_URL}/items/{item_id}").json()
if maintenance_item["status"] == "maintenance":
    print("PASS  item status is 'maintenance' after breakdown")
else:
    print(f"FAIL  item status is '{maintenance_item['status']}' after breakdown (expected 'maintenance')")
    failures.append("item status after breakdown")

# 11. Breakdown: mark repaired via the dedicated endpoint
check(
    "mark repaired (POST /repair)",
    requests.post(f"{BASE_URL}/breakdowns/{breakdown_id}/repair", json={
        "repairer_id": user_id, "repaired_date": today.isoformat(),
    }),
    200,
)
repaired_item = requests.get(f"{BASE_URL}/items/{item_id}").json()
if repaired_item["status"] == "available":
    print("PASS  item status is 'available' after repair")
else:
    print(f"FAIL  item status is '{repaired_item['status']}' after repair (expected 'available')")
    failures.append("item status after repair")

# 12. Transfer between storages
storage2 = check(
    "create second storage",
    requests.post(f"{BASE_URL}/storages/", json={"name": f"test-storage2-{stamp}", "address": "ул. Горная, 2", "club_id": club_id}),
    201,
)
storage2_id = storage2["id"]
check(
    "transfer item to storage2",
    requests.post(f"{BASE_URL}/transfers/", json={
        "item_id": item_id, "from_storage_id": storage_id, "to_storage_id": storage2_id,
        "date": today.isoformat(), "mover_id": user_id,
        "comment": "передали в другой клуб",
    }),
    201,
)
moved_item = requests.get(f"{BASE_URL}/items/{item_id}").json()
if moved_item["storage_id"] == storage2_id:
    print("PASS  item storage updated after transfer")
else:
    print(f"FAIL  item storage is {moved_item['storage_id']} (expected {storage2_id})")
    failures.append("item storage after transfer")
# 12a. Transfer from a wrong source storage is rejected
bad_transfer = requests.post(f"{BASE_URL}/transfers/", json={
    "item_id": item_id, "from_storage_id": storage_id, "to_storage_id": storage2_id,
    "date": today.isoformat(),
})
if bad_transfer.status_code == 400:
    print("PASS  transfer from wrong source rejected with 400")
else:
    print(f"FAIL  bad transfer: {bad_transfer.status_code} (expected 400)")
    failures.append("bad transfer")
check("transfer history", requests.get(f"{BASE_URL}/transfers/item/{item_id}"))

# 13. Auth: register + login + me
auth_password = "S3cure-pass"
reg = requests.post(f"{BASE_URL}/auth/register", json={
    "name": "Аут", "surname": "Тестов", "email": f"auth-{stamp}@example.com",
    "phone": f"+7902{stamp[-7:]}", "password": auth_password,
})
if reg.status_code == 201:
    print("PASS  auth register: 201")
else:
    print(f"FAIL  auth register: {reg.status_code} {reg.text[:150]}")
    failures.append("auth register")
login = requests.post(f"{BASE_URL}/auth/login", json={
    "email": f"auth-{stamp}@example.com", "password": auth_password,
})
if login.status_code == 200 and "access_token" in login.json():
    print("PASS  auth login: 200 with token")
    token = login.json()["access_token"]
    me = requests.get(f"{BASE_URL}/auth/me", headers={"Authorization": f"Bearer {token}"})
    if me.status_code == 200:
        print("PASS  /auth/me returns the user")
    else:
        print(f"FAIL  /auth/me: {me.status_code}")
        failures.append("auth me")
    bad_login = requests.post(f"{BASE_URL}/auth/login", json={
        "email": f"auth-{stamp}@example.com", "password": "wrong",
    })
    if bad_login.status_code == 401:
        print("PASS  wrong password rejected with 401")
    else:
        print(f"FAIL  wrong password: {bad_login.status_code} (expected 401)")
        failures.append("auth wrong password")
else:
    print(f"FAIL  auth login: {login.status_code} {login.text[:150]}")
    failures.append("auth login")

# 14. Reads back
check("get item", requests.get(f"{BASE_URL}/items/{item_id}"))
check("list storages", requests.get(f"{BASE_URL}/storages"))
check("item parameters", requests.get(f"{BASE_URL}/item-parameters/item/{item_id}"))
check("distributions by item", requests.get(f"{BASE_URL}/distributions/item/{item_id}"))
check("breakdowns by item", requests.get(f"{BASE_URL}/breakdowns/item/{item_id}"))
check("active distributions", requests.get(f"{BASE_URL}/distributions/active/"))

print()
if failures:
    print(f"RESULT: {len(failures)} FAILED: {failures}")
    sys.exit(1)
print("RESULT: ALL CHECKS PASSED")
