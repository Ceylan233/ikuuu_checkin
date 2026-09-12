import importlib.util
import base64
import os
import unittest
from unittest.mock import patch
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

    def test_login_page_uses_html_headers_and_new_phase(self):
        module = load_module()

        class Response:
            text = "<script>const captchaId = 'cc96d05ba8b60f9112f76e18526fcb73';</script>"
            url = "https://ikuuu.example/auth/login"

            @staticmethod
            def raise_for_status():
                return None

        class Session:
            request_headers = None

            def get(self, url, headers, timeout, allow_redirects):
                self.request_headers = headers
                return Response()

        session = Session()
        login_opts = {
            "remember_me": "off",
            "captcha_result": {},
            "captcha_solver": {"enabled": True},
        }
        solution = {
            "lot_number": "lot",
            "captcha_output": "output",
            "pass_token": "token",
            "gen_time": "time",
        }

        with patch.object(module, "solve_geetest_v4", return_value=(solution, None)):
            body, post_base_url, error = module.build_login_body(
                "https://ikuuu.example", "user@example.com", "password", login_opts, session
            )

        self.assertIsNone(error)
        self.assertEqual(post_base_url, "https://ikuuu.example")
        self.assertIn("text/html", session.request_headers["Accept"])
        self.assertEqual(body["phase"], "password")
        self.assertEqual(body["host"], "ikuuu.example")
        self.assertNotIn("remember_me", body)
        self.assertEqual(body["captcha_result[lot_number]"], "lot")

    def test_new_and_legacy_login_success_formats(self):
        module = load_module()

        self.assertTrue(module.login_response_authenticated({"phase": "authenticated"}))
        self.assertTrue(module.login_response_authenticated({"ret": 1}))
        self.assertFalse(module.login_response_authenticated({"phase": "password", "ret": 0}))

    def test_domain_announcement_is_not_a_login_page(self):
        module = load_module()
        announcement = "<html><title>iKuuuVPN最新域名</title><h3>ikuuu.top</h3></html>"

        self.assertFalse(module.is_login_page_content(announcement))

    def test_wrapped_real_login_page_is_detected(self):
        module = load_module()
        login_html = (
            '<form><input name="email"><input name="password"></form>'
            '<script>function submitLogin(){$.post("/auth/login");}</script>'
        )
        encoded = base64.b64encode(login_html.encode()).decode()
        wrapped = f'<script>var originBody = "{encoded}";</script>'

        self.assertTrue(module.is_login_page_content(wrapped))

    def test_host_reachable_requires_real_login_page(self):
        module = load_module()
        response = mock_response = type(
            "Response",
            (),
            {
                "status_code": 200,
                "text": "<html><title>最新域名</title></html>",
            },
        )()

        with patch.object(module.requests, "get", return_value=response):
            with patch("builtins.print"):
                self.assertFalse(module.test_host_reachable("old.example"))

        self.assertEqual(mock_response.status_code, 200)


if __name__ == "__main__":
    unittest.main()
