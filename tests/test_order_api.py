import sys
from datetime import UTC, datetime
from pathlib import Path
from unittest import TestCase
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import psycopg
from fastapi.testclient import TestClient

from system_auditor.main import (
    OrderItemResponse,
    OrderResponse,
    OrderSummaryResponse,
    _pool_settings,
    app,
)


def sample_order() -> OrderResponse:
    return OrderResponse(
        id=12,
        user_id=7,
        status="pending",
        ordered_at=datetime(2026, 10, 15, tzinfo=UTC),
        total_cents=3_998,
        items=[
            OrderItemResponse(
                item_id=3,
                sku="SKU-000003",
                name="Seed Item 3",
                quantity=2,
                unit_price_cents=1_999,
                line_total_cents=3_998,
            )
        ],
    )


class OrderApiTests(TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    @patch("system_auditor.main._get_order", return_value=sample_order())
    def test_get_order_returns_order_and_items(self, get_order: object) -> None:
        response = self.client.get("/orders/12")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["id"], 12)
        self.assertEqual(response.json()["items"][0]["item_id"], 3)
        get_order.assert_called_once_with(12)

    @patch("system_auditor.main._get_order", return_value=None)
    def test_get_order_returns_404_when_absent(self, _: object) -> None:
        response = self.client.get("/orders/999")

        self.assertEqual(response.status_code, 404)

    @patch(
        "system_auditor.main._get_order",
        side_effect=psycopg.OperationalError("database connection failed"),
    )
    def test_get_order_hides_database_error_details(self, _: object) -> None:
        response = self.client.get("/orders/12")

        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["detail"], "Database unavailable")

    @patch(
        "system_auditor.main._list_user_orders",
        return_value=[
            OrderSummaryResponse(
                id=12,
                user_id=7,
                status="pending",
                ordered_at=datetime(2026, 10, 15, tzinfo=UTC),
                total_cents=3_998,
            )
        ],
    )
    def test_list_orders_for_user_honors_pagination(self, list_orders: object) -> None:
        response = self.client.get("/users/7/orders?limit=10&offset=20")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()[0]["user_id"], 7)
        list_orders.assert_called_once_with(7, 10, 20)

    @patch("system_auditor.main._create_order", return_value=sample_order())
    def test_create_order_returns_created_order(self, create_order: object) -> None:
        response = self.client.post(
            "/orders",
            json={"user_id": 7, "items": [{"item_id": 3, "quantity": 2}]},
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["total_cents"], 3_998)
        self.assertEqual(create_order.call_args.args[0].user_id, 7)

    @patch("system_auditor.main._create_order")
    def test_create_order_rejects_duplicate_items(self, create_order: object) -> None:
        response = self.client.post(
            "/orders",
            json={
                "user_id": 7,
                "items": [
                    {"item_id": 3, "quantity": 1},
                    {"item_id": 3, "quantity": 2},
                ],
            },
        )

        self.assertEqual(response.status_code, 422)
        create_order.assert_not_called()

    @patch("system_auditor.main._create_order", return_value=None)
    def test_create_order_returns_404_for_missing_resource(self, _: object) -> None:
        response = self.client.post(
            "/orders",
            json={"user_id": 7, "items": [{"item_id": 3, "quantity": 2}]},
        )

        self.assertEqual(response.status_code, 404)

    def test_pool_settings_accept_bounded_configuration(self) -> None:
        with patch.dict(
            "system_auditor.main.os.environ",
            {
                "POSTGRES_POOL_MIN_SIZE": "1",
                "POSTGRES_POOL_MAX_SIZE": "4",
                "POSTGRES_POOL_TIMEOUT_SECONDS": "3",
                "POSTGRES_POOL_MAX_WAITING": "32",
            },
            clear=True,
        ):
            self.assertEqual(_pool_settings(), (1, 4, 3.0, 32))

    def test_pool_settings_reject_invalid_sizes(self) -> None:
        with (
            patch.dict(
                "system_auditor.main.os.environ",
                {
                    "POSTGRES_POOL_MIN_SIZE": "4",
                    "POSTGRES_POOL_MAX_SIZE": "1",
                    "POSTGRES_POOL_TIMEOUT_SECONDS": "3",
                    "POSTGRES_POOL_MAX_WAITING": "32",
                },
                clear=True,
            ),
            self.assertRaises(ValueError),
        ):
            _pool_settings()

    @patch("system_auditor.main._get_order", return_value=sample_order())
    @patch("system_auditor.main._build_postgres_pool")
    def test_lifespan_opens_and_closes_pool(self, build_pool: Mock, _: Mock) -> None:
        pool = Mock(timeout=3)
        build_pool.return_value = pool

        with TestClient(app) as client:
            self.assertEqual(client.get("/orders/12").status_code, 200)

        pool.open.assert_called_once_with(wait=True, timeout=3)
        pool.close.assert_called_once_with()
