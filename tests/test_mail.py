import importlib.util
from contextlib import ExitStack
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
    def test_accounts_accept_optional_mailbox_authorization_code(self):
        environment = {
            "ACCOUNTS": (
                "first@example.com:ikuuu-password\n"
                "second@qq.com:another-password:mail:authorization:code"
            )
        }
        with mock.patch.dict(os.environ, environment, clear=True):
            monitor = load_monitor()
            with mock.patch("builtins.print"):
                self.assertEqual(
                    monitor.get_accounts(),
                    [
                        ("first@example.com", "ikuuu-password", ""),
                        (
                            "second@qq.com",
                            "another-password",
                            "mail:authorization:code",
                        ),
                    ],
                )

    def test_extracts_eight_digit_code_from_ikuuu_email(self):
        monitor = load_monitor()
        message = (
            b"Subject: iKuuu login verification code\r\n"
            b"Content-Type: text/plain; charset=utf-8\r\n"
            b"\r\n"
            b"Your iKuuu login verification code is 12345678.\r\n"
        )
        self.assertEqual(monitor.extract_login_email_code(message), "12345678")
        self.assertIsNone(
            monitor.extract_login_email_code(
                b"Subject: Newsletter\r\n\r\nReference number: 12345678\r\n"
            )
        )

    def test_email_code_phase_submits_code_on_same_session(self):
        monitor = load_monitor()
        session = mock.Mock()
        initial_body = {"host": "ikuuu.example", "phase": "password"}
        with ExitStack() as stack:
            stack.enter_context(
                mock.patch.object(monitor.requests, "session", return_value=session)
            )
            stack.enter_context(mock.patch.object(monitor, "get_login_opts", return_value={}))
            stack.enter_context(
                mock.patch.object(monitor, "load_session_cookie", return_value=None)
            )
            stack.enter_context(
                mock.patch.object(
                    monitor,
                    "build_login_body",
                    return_value=(initial_body, "https://ikuuu.example", None),
                )
            )
            submit_login_request = stack.enter_context(
                mock.patch.object(
                    monitor,
                    "submit_login_request",
                    side_effect=[({"phase": "email_code"}, None), ({"ret": 1}, None)],
                )
            )
            wait_for_login_email_code = stack.enter_context(
                mock.patch.object(
                    monitor,
                    "wait_for_login_email_code",
                    return_value=("12345678", None),
                )
            )
            stack.enter_context(mock.patch.object(monitor, "save_session_cookie"))
            stack.enter_context(
                mock.patch.object(
                    monitor,
                    "do_checkin_with_session",
                    return_value=(True, "签到成功", "10", "GB"),
                )
            )
            stack.enter_context(
                mock.patch.object(
                    monitor,
                    "get_user_info",
                    return_value=("10 GB", "1", "2026-12-31", "0"),
                )
            )
            with mock.patch("builtins.print"):
                result = monitor.ikuuu_signin(
                    "user@example.com", "ikuuu-password", "mail-authorization-code"
                )

        self.assertTrue(result[0])
        wait_for_login_email_code.assert_called_once()
        self.assertEqual(submit_login_request.call_count, 2)
        self.assertEqual(submit_login_request.call_args_list[1].args[0], session)
        self.assertEqual(
            submit_login_request.call_args_list[1].args[2],
            {
                "host": "ikuuu.example",
                "phase": "email_code",
                "email_code": "12345678",
            },
        )
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
