import asyncio
import unittest

import httpx

from system_auditor import __version__
from system_auditor.main import app


class PackageTests(unittest.TestCase):
    async def _get(self, path: str) -> httpx.Response:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            return await client.get(path)

    def test_package_version_is_available(self):
        self.assertEqual(__version__, "0.1.0")

    def test_hello_endpoint(self):
        response = asyncio.run(self._get("/hello"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"message": "Hello, world!"})

    def test_health_endpoint(self):
        response = asyncio.run(self._get("/health"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})


if __name__ == "__main__":
    unittest.main()
