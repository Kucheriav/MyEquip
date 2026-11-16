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

# 9. Distribution: return
check(
    "return item",
    requests.put(f"{BASE_URL}/distributions/{distribution_id}", json={
        "status": "returned", "accepter_id": user_id,
        "accepting_date": today.isoformat(),
    }),
    200,
)

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

# 11. Breakdown: mark repaired
check(
    "mark repaired",
    requests.put(f"{BASE_URL}/breakdowns/{breakdown_id}", json={
        "repaired_date": today.isoformat(), "repairer_id": user_id,
    }),
    200,
)

# 12. Reads back
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
