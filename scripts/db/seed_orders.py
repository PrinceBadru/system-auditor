from __future__ import annotations

import argparse
import os
from pathlib import Path

import psycopg

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = ROOT / "scripts" / "db" / "schema.sql"


def connection_info() -> dict[str, object]:
    return {
        "host": os.environ.get("POSTGRES_HOST", "localhost"),
        "port": int(os.environ.get("POSTGRES_PORT", "5432")),
        "dbname": os.environ.get("POSTGRES_DB", "system_auditor"),
        "user": os.environ.get("POSTGRES_USER", "system_auditor"),
        "password": os.environ["POSTGRES_PASSWORD"],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create the relational order schema and seed synthetic data."
    )
    parser.add_argument("--orders", type=int, default=100_000)
    parser.add_argument("--users", type=int, default=10_000)
    parser.add_argument("--items", type=int, default=1_000)
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Truncate order, item, and user tables before seeding.",
    )
    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> None:
    for name in ("orders", "users", "items"):
        value = getattr(args, name)
        if value < 1:
            raise ValueError(f"--{name} must be at least 1")


def apply_schema(connection: psycopg.Connection) -> None:
    connection.execute(SCHEMA_PATH.read_text(encoding="utf-8"))


def reset_tables(connection: psycopg.Connection) -> None:
    connection.execute(
        "TRUNCATE TABLE order_items, orders, items, users RESTART IDENTITY CASCADE"
    )


def seed_users(connection: psycopg.Connection, count: int) -> None:
    connection.execute(
        """
        INSERT INTO users (email, full_name, created_at)
        SELECT
            format('seed-user-%s@example.test', user_no),
            format('Seed User %s', user_no),
            now() - (user_no % 365) * interval '1 day'
        FROM generate_series(1, %(count)s) AS seed(user_no)
        ON CONFLICT (email) DO NOTHING
        """,
        {"count": count},
    )


def seed_items(connection: psycopg.Connection, count: int) -> None:
    connection.execute(
        """
        INSERT INTO items (sku, name, unit_price_cents, active, created_at)
        SELECT
            format('SKU-%s', lpad(item_no::text, 6, '0')),
            format('Seed Item %s', item_no),
            100 + ((item_no * 37) % 9900),
            true,
            now() - (item_no % 90) * interval '1 day'
        FROM generate_series(1, %(count)s) AS seed(item_no)
        ON CONFLICT (sku) DO NOTHING
        """,
        {"count": count},
    )


def seed_orders(
    connection: psycopg.Connection, orders: int, users: int, items: int
) -> int:
    result = connection.execute(
        """
        WITH seeded_users AS (
            SELECT id, row_number() OVER (ORDER BY id) AS user_no
            FROM users
            WHERE email LIKE 'seed-user-%%@example.test'
            ORDER BY id
            LIMIT %(users)s
        ),
        seeded_items AS (
            SELECT id, unit_price_cents, row_number() OVER (ORDER BY id) AS item_no
            FROM items
            WHERE sku LIKE 'SKU-%%'
            ORDER BY id
            LIMIT %(items)s
        ),
        inserted_orders AS (
            INSERT INTO orders (user_id, status, ordered_at)
            SELECT
                seeded_users.id,
                CASE order_seed.order_no %% 4
                    WHEN 0 THEN 'pending'
                    WHEN 1 THEN 'paid'
                    WHEN 2 THEN 'shipped'
                    ELSE 'cancelled'
                END,
                now() - (order_seed.order_no %% 730) * interval '1 day'
            FROM generate_series(1, %(orders)s) AS order_seed(order_no)
            JOIN seeded_users
                ON seeded_users.user_no = ((order_seed.order_no - 1) %% %(users)s) + 1
            RETURNING id
        ),
        numbered_orders AS (
            SELECT id, row_number() OVER (ORDER BY id) AS order_no
            FROM inserted_orders
        ),
        inserted_lines AS (
            INSERT INTO order_items (order_id, item_id, quantity, unit_price_cents)
            SELECT
                numbered_orders.id,
                seeded_items.id,
                ((numbered_orders.order_no + line_seed.line_no) %% 5) + 1,
                seeded_items.unit_price_cents
            FROM numbered_orders
            CROSS JOIN LATERAL generate_series(
                1,
                LEAST(%(items)s, (numbered_orders.order_no %% 5) + 1)
            ) AS line_seed(line_no)
            JOIN seeded_items
                ON seeded_items.item_no =
                    ((numbered_orders.order_no + line_seed.line_no - 2) %% %(items)s) + 1
            RETURNING order_id, line_total_cents
        ),
        order_totals AS (
            SELECT order_id, sum(line_total_cents)::integer AS total_cents
            FROM inserted_lines
            GROUP BY order_id
        ),
        updated_orders AS (
            UPDATE orders
            SET total_cents = order_totals.total_cents
            FROM order_totals
            WHERE orders.id = order_totals.order_id
            RETURNING orders.id
        )
        SELECT count(*) FROM updated_orders
        """,
        {"orders": orders, "users": users, "items": items},
    ).fetchone()
    return int(result[0])


def main() -> None:
    args = parse_args()
    validate_args(args)

    with psycopg.connect(**connection_info()) as connection:
        apply_schema(connection)
        if args.reset:
            reset_tables(connection)
        seed_users(connection, args.users)
        seed_items(connection, args.items)
        created_orders = seed_orders(connection, args.orders, args.users, args.items)

    print(
        f"Seeded {created_orders:,} orders with "
        f"{args.users:,} users and {args.items:,} items."
    )


if __name__ == "__main__":
    main()
