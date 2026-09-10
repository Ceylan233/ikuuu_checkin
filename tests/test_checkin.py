import importlib.util
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).resolve().parents[1] / "auto_check_in_ikuuu.py"


def load_monitor():
    spec = importlib.util.spec_from_file_location("ikuuu_checkin_retry", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class Response:
    def __init__(self, url, payload=None, text="", content_type="text/html"):
        self.url = url
        self.status_code = 200
        self._payload = payload
        self.text = text
        self.headers = {"Content-Type": content_type}

    def json(self):
        if self._payload is None:
            raise ValueError("not json")
        return self._payload


class CheckinTests(unittest.TestCase):
    def test_checkin_retries_after_login_page_then_succeeds(self):
        monitor = load_monitor()
        session = mock.Mock()
        session.post.side_effect = [
            Response("https://ikuuu.example/auth/login", text="<html></html>"),
            Response(
                "https://ikuuu.example/user/checkin",
                payload={"ret": 1, "msg": "签到成功"},
            ),
        ]

        with mock.patch.object(
            monitor, "get_remaining_flow", return_value=("10", "GB")
        ) as get_remaining_flow, mock.patch.object(monitor.time, "sleep") as sleep:
            success, message, flow, unit = monitor.do_checkin_with_session(
                session, "https://ikuuu.example"
            )

        self.assertTrue(success)
        self.assertIn("签到成功", message)
        self.assertEqual((flow, unit), ("10", "GB"))
        self.assertEqual(session.post.call_count, 2)
        get_remaining_flow.assert_called_once_with(session, "https://ikuuu.example")
        sleep.assert_called_once_with(2)
        headers = session.post.call_args.kwargs["headers"]
        self.assertEqual(headers["Origin"], "https://ikuuu.example")
        self.assertEqual(headers["Referer"], "https://ikuuu.example/user")

    def test_remaining_flow_uses_authenticated_session_and_actual_domain(self):
        monitor = load_monitor()
        html = (
            '<div class="card card-statistic-2"><h4>剩余流量</h4>'
            '<span class="counter">12.34</span> GB</div>'
        )
        import base64

        wrapped = 'var originBody = "' + base64.b64encode(html.encode()).decode() + '"'
        response = Response("https://ikuuu.example/user", text=wrapped)
        session = mock.Mock()
        session.get.return_value = response

        flow, unit = monitor.get_remaining_flow(session, "https://ikuuu.example")

        self.assertEqual((flow, unit), ("12.34", "GB"))
        session.get.assert_called_once_with(
            "https://ikuuu.example/user",
            headers={"User-Agent": monitor.USER_AGENT},
            timeout=20,
            allow_redirects=True,
        )


if __name__ == "__main__":
    unittest.main()
