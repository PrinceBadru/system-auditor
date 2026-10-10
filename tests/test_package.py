import unittest

from system_auditor import __version__


class PackageTests(unittest.TestCase):
    def test_package_version_is_available(self):
        self.assertEqual(__version__, "0.1.0")


if __name__ == "__main__":
    unittest.main()
