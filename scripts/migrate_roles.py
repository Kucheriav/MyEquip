"""One-off migration for the role/club-membership schema.

Run ONCE against the real database with the API server STOPPED:

    python scripts/migrate_roles.py

It preserves existing data:
  * users.role            (leader for status='full', tourist otherwise)
  * club_members          (leader of each club + tourists/storekeepers)
  * items.club_id         (from the item's category / storage)
  * invite_codes.role/club_id
  * drops the unused user_in_club table and items.owner_id

The script is safe to re-run: every DDL step checks whether it has
already been applied.
"""
import os
import sys

# Running this file directly puts scripts/ (not the project root) on
# sys.path, so `import app...` would fail. Add the project root explicitly.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from sqlalchemy import text

from app.config import config
from app.database import engine


def table_exists(conn, table: str) -> bool:
    return conn.execute(
        text(
            "SELECT COUNT(*) FROM information_schema.tables "
            "WHERE table_schema = DATABASE() AND table_name = :t"
        ),
        {"t": table},
    ).scalar() > 0


def column_exists(conn, table: str, column: str) -> bool:
    return conn.execute(
        text(
            "SELECT COUNT(*) FROM information_schema.columns "
            "WHERE table_schema = DATABASE() AND table_name = :t AND column_name = :c"
        ),
        {"t": table, "c": column},
    ).scalar() > 0


def foreign_key_name(conn, table: str, column: str):
    return conn.execute(
        text(
            "SELECT CONSTRAINT_NAME FROM information_schema.KEY_COLUMN_USAGE "
            "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :t "
            "AND COLUMN_NAME = :c AND REFERENCED_TABLE_NAME IS NOT NULL LIMIT 1"
        ),
        {"t": table, "c": column},
    ).scalar()


def index_exists(conn, table: str, index: str) -> bool:
    return conn.execute(
        text(
            "SELECT COUNT(*) FROM information_schema.statistics "
            "WHERE table_schema = DATABASE() AND table_name = :t AND index_name = :i"
        ),
        {"t": table, "i": index},
    ).scalar() > 0


def fetch(conn, sql: str, **params):
    return [dict(row._mapping) for row in conn.execute(text(sql), params)]


def main():
    print(f"Database: {config.DB_NAME} @ {config.DB_HOST}:{config.DB_PORT}")
    print("Make sure the API server is stopped and you have a backup.\n")

    with engine.begin() as conn:
        # ---------------------------------------------------------------
        # 1. users.role
        # ---------------------------------------------------------------
        if not column_exists(conn, "users", "role"):
            conn.execute(text(
                "ALTER TABLE users ADD COLUMN role "
                "ENUM('leader','storekeeper','tourist') NOT NULL DEFAULT 'tourist'"
            ))
            print("+ users.role")
        else:
            print("= users.role already exists")

        conn.execute(text(
            "UPDATE users SET role = 'leader' WHERE status = 'full' AND role <> 'leader'"
        ))

        # ---------------------------------------------------------------
        # 2. club_members
        # ---------------------------------------------------------------
        if not table_exists(conn, "club_members"):
            conn.execute(text(
                "CREATE TABLE club_members ("
                " id INT NOT NULL AUTO_INCREMENT,"
                " user_id INT NOT NULL,"
                " club_id INT NOT NULL,"
                " role ENUM('leader','storekeeper','tourist') NOT NULL DEFAULT 'tourist',"
                " PRIMARY KEY (id),"
                " UNIQUE KEY uq_club_member (user_id, club_id),"
                " KEY ix_club_members_user_id (user_id),"
                " KEY ix_club_members_club_id (club_id),"
                " CONSTRAINT fk_club_members_user FOREIGN KEY (user_id) REFERENCES users(id),"
                " CONSTRAINT fk_club_members_club FOREIGN KEY (club_id) REFERENCES clubs(id)"
                ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"
            ))
            print("+ club_members")
        else:
            print("= club_members already exists")

        # ---------------------------------------------------------------
        # 3. invite_codes.role / club_id
        # ---------------------------------------------------------------
        if not column_exists(conn, "invite_codes", "role"):
            conn.execute(text(
                "ALTER TABLE invite_codes ADD COLUMN role "
                "ENUM('leader','storekeeper') NOT NULL DEFAULT 'leader'"
            ))
            print("+ invite_codes.role")
        if not column_exists(conn, "invite_codes", "club_id"):
            conn.execute(text("ALTER TABLE invite_codes ADD COLUMN club_id INT NULL"))
            conn.execute(text(
                "ALTER TABLE invite_codes ADD CONSTRAINT fk_invite_codes_club "
                "FOREIGN KEY (club_id) REFERENCES clubs(id)"
            ))
            print("+ invite_codes.club_id")

        # ---------------------------------------------------------------
        # 4. Backfill club membership from the old data
        # ---------------------------------------------------------------
        users = fetch(conn, "SELECT id, status, role FROM users")
        clubs = fetch(conn, "SELECT id, name FROM clubs")
        item_owners = fetch(conn, """
            SELECT u.id AS user_id, c.club_id AS club_id, COUNT(*) AS cnt
            FROM items i
            JOIN categories c ON c.id = i.category_id
            JOIN users u ON u.id = i.owner_id
            GROUP BY u.id, c.club_id
        """) if column_exists(conn, "items", "owner_id") else []

        if table_exists(conn, "user_in_club"):
            legacy_links = fetch(conn, "SELECT user_id, club_id, privileges FROM user_in_club")
        else:
            legacy_links = []

        full_ids = {u["id"] for u in users if u["status"] == "full"}
        items_by_user_club = {(r["user_id"], r["club_id"]): r["cnt"] for r in item_owners}

        def upsert_membership(user_id, club_id, role):
            existing = conn.execute(
                text("SELECT id, role FROM club_members WHERE user_id = :u AND club_id = :c"),
                {"u": user_id, "c": club_id},
            ).first()
            if existing:
                # Never downgrade a leader
                if existing.role != "leader":
                    conn.execute(
                        text("UPDATE club_members SET role = :r WHERE id = :i"),
                        {"r": role, "i": existing.id},
                    )
                return
            conn.execute(
                text(
                    "INSERT INTO club_members (user_id, club_id, role) "
                    "VALUES (:u, :c, :r)"
                ),
                {"u": user_id, "c": club_id, "r": role},
            )

        # Legacy user_in_club links first (the table was unused, usually empty)
        for link in legacy_links:
            role = {"owner": "leader", "giver": "storekeeper"}.get(link["privileges"], "tourist")
            upsert_membership(link["user_id"], link["club_id"], role)
            if role == "storekeeper" and link["user_id"] not in full_ids:
                conn.execute(
                    text("UPDATE users SET role = 'storekeeper' WHERE id = :u AND role = 'tourist'"),
                    {"u": link["user_id"]},
                )

        # Every club needs a leader: the full user with most items in that
        # club, otherwise the only full user, otherwise any full user.
        for club in clubs:
            club_id = club["id"]
            has_leader = conn.execute(
                text("SELECT COUNT(*) FROM club_members WHERE club_id = :c AND role = 'leader'"),
                {"c": club_id},
            ).scalar()
            if has_leader:
                continue

            candidates = sorted(
                ((items_by_user_club.get((uid, club_id), 0), uid) for uid in full_ids),
                reverse=True,
            )
            leader_id = candidates[0][1] if candidates and candidates[0][0] > 0 else None
            if leader_id is None and len(full_ids) == 1:
                leader_id = next(iter(full_ids))
            if leader_id is None and candidates:
                leader_id = candidates[0][1]

            if leader_id is None:
                print(f"! club {club['id']} ({club['name']}): no leader candidate found")
                continue
            upsert_membership(leader_id, club_id, "leader")
            print(f"+ club {club['id']} ({club['name']}): leader = user {leader_id}")

        # Other item owners become tourists of the corresponding club
        for (user_id, club_id), _cnt in items_by_user_club.items():
            upsert_membership(user_id, club_id, "tourist")

        # A user with no links at all (e.g. a guest recorded but never
        # attached to a club) goes to the only club so that nothing
        # disappears from the leader's lists.
        if len(clubs) == 1:
            single_club_id = clubs[0]["id"]
            for user in users:
                has_membership = conn.execute(
                    text("SELECT COUNT(*) FROM club_members WHERE user_id = :u"),
                    {"u": user["id"]},
                ).scalar()
                if not has_membership:
                    upsert_membership(user["id"], single_club_id, "tourist")
                    print(f"+ user {user['id']}: tourist of club {single_club_id}")

        # ---------------------------------------------------------------
        # 5. items.club_id from category / storage, then drop owner_id
        # ---------------------------------------------------------------
        if not column_exists(conn, "items", "club_id"):
            conn.execute(text("ALTER TABLE items ADD COLUMN club_id INT NULL"))
            print("+ items.club_id (nullable, backfilling)")

        conn.execute(text("""
            UPDATE items i
            JOIN categories c ON c.id = i.category_id
            SET i.club_id = c.club_id
            WHERE i.club_id IS NULL
        """))
        conn.execute(text("""
            UPDATE items i
            JOIN storages s ON s.id = i.storage_id
            SET i.club_id = s.club_id
            WHERE i.club_id IS NULL
        """))

        missing = conn.execute(
            text("SELECT COUNT(*) FROM items WHERE club_id IS NULL")
        ).scalar()
        if missing:
            raise SystemExit(
                f"ABORT: {missing} item(s) have no club (bad category/storage). "
                "Fix them manually and re-run."
            )

        conn.execute(text("ALTER TABLE items MODIFY club_id INT NOT NULL"))

        if not index_exists(conn, "items", "ix_items_club_id"):
            conn.execute(text("ALTER TABLE items ADD KEY ix_items_club_id (club_id)"))

        if not foreign_key_name(conn, "items", "club_id"):
            conn.execute(text(
                "ALTER TABLE items ADD CONSTRAINT fk_items_club "
                "FOREIGN KEY (club_id) REFERENCES clubs(id)"
            ))
        print("+ items.club_id backfilled")

        if column_exists(conn, "items", "owner_id"):
            fk = foreign_key_name(conn, "items", "owner_id")
            if fk:
                conn.execute(text(f"ALTER TABLE items DROP FOREIGN KEY {fk}"))
            conn.execute(text("ALTER TABLE items DROP COLUMN owner_id"))
            print("- items.owner_id")

        # ---------------------------------------------------------------
        # 6. Drop the unused user_in_club table
        # ---------------------------------------------------------------
        if table_exists(conn, "user_in_club"):
            conn.execute(text("DROP TABLE user_in_club"))
            print("- user_in_club")

        # ---------------------------------------------------------------
        # Summary
        # ---------------------------------------------------------------
        print("\nSummary:")
        for row in fetch(conn, "SELECT role, COUNT(*) AS n FROM users GROUP BY role"):
            print(f"  users {row['role']}: {row['n']}")
        for row in fetch(conn, "SELECT role, COUNT(*) AS n FROM club_members GROUP BY role"):
            print(f"  members {row['role']}: {row['n']}")
        print(f"  items with club: {conn.execute(text('SELECT COUNT(*) FROM items')).scalar()}")


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001
        print(f"\nMIGRATION FAILED: {exc}")
        sys.exit(1)
