import importlib.util
import os
import unittest
from pathlib import Path
from unittest import mock


SCRIPT = Path(__file__).resolve().parents[1] / "auto_check_in_ikuuu.py"


def load_monitor():
    spec = importlib.util.spec_from_file_location("ikuuu_checkin", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class MailTests(unittest.TestCase):
    def test_provider_inference_and_recipients(self):
        monitor = load_monitor()
        self.assertEqual(monitor.infer_mail_provider("sender@qq.com"), "qq")
        self.assertEqual(
            monitor.parse_recipients("one@example.com; two@example.com,three@example.com"),
            ["one@example.com", "two@example.com", "three@example.com"],
        )

    def test_outlook_settings(self):
        with mock.patch.dict(os.environ, {"MAIL_PROVIDER": "outlook"}, clear=True):
            monitor = load_monitor()
            self.assertEqual(
                monitor.smtp_settings("sender@outlook.com"),
                ("smtp-mail.outlook.com", 587, "starttls"),
            )

    def test_custom_username_and_multiple_recipients(self):
        environment = {
            "MAIL_PROVIDER": "custom",
            "MAIL_USER": "sender@example.com",
            "MAIL_PASS": "app-password",
            "MAIL_TO": "one@example.com,two@example.com",
            "SMTP_HOST": "mail.example.com",
            "SMTP_PORT": "465",
            "SMTP_SECURITY": "ssl",
            "SMTP_USERNAME": "smtp-login",
        }
        with mock.patch.dict(os.environ, environment, clear=True):
            monitor = load_monitor()
            with mock.patch.object(monitor.smtplib, "SMTP_SSL") as smtp_ssl:
                client = smtp_ssl.return_value.__enter__.return_value
                monitor.send_smtp_mail("test", "body")
            client.login.assert_called_once_with("smtp-login", "app-password")
            self.assertEqual(
                client.send_message.call_args.kwargs["to_addrs"],
                ["one@example.com", "two@example.com"],
            )


if __name__ == "__main__":
    unittest.main()
