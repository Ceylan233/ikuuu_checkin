import importlib.util
import os
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "auto_check_in_ikuuu.py"


def load_module():
    spec = importlib.util.spec_from_file_location("ikuuu_checkin_domain", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class DomainTests(unittest.TestCase):
    def test_normalize_ikuuu_host(self):
        module = load_module()

        self.assertEqual(module.normalize_ikuuu_host("ikuuu.example"), "ikuuu.example")
        self.assertEqual(module.normalize_ikuuu_host(" https://IKUUU.example/ "), "ikuuu.example")
        self.assertEqual(module.normalize_ikuuu_host("https://ikuuu.example/auth/login"), "ikuuu.example")
        self.assertEqual(module.normalize_ikuuu_host("ikuuu.example:8443"), "ikuuu.example:8443")
        self.assertEqual(module.normalize_ikuuu_host(""), "")
        self.assertEqual(module.normalize_ikuuu_host("ftp://ikuuu.example"), "")

    def test_custom_domain_has_priority(self):
        previous = os.environ.get("IKUUU_DOMAIN")
        os.environ["IKUUU_DOMAIN"] = "https://custom.ikuuu.example/"
        try:
            module = load_module()
            self.assertEqual(module.custom_ikun_host, "custom.ikuuu.example")
            self.assertEqual(module.ikun_host, "custom.ikuuu.example")
        finally:
            if previous is None:
                os.environ.pop("IKUUU_DOMAIN", None)
            else:
                os.environ["IKUUU_DOMAIN"] = previous


if __name__ == "__main__":
    unittest.main()
