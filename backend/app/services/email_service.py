"""Shared email service for all apps. Uses SMTP with HTML templates."""
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging

logger = logging.getLogger(__name__)


class EmailService:
    def __init__(self, host: str, port: int, user: str, password: str, from_addr: str, app_name: str):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.from_addr = from_addr
        self.app_name = app_name

    def _send(self, to: str, subject: str, html: str) -> bool:
        try:
            msg = MIMEMultipart("alternative")
            msg["From"] = self.from_addr
            msg["To"] = to
            msg["Subject"] = subject
            msg.attach(MIMEText(html, "html"))
            with smtplib.SMTP(self.host, self.port, timeout=10) as server:
                server.starttls()
                server.login(self.user, self.password)
                server.send_message(msg)
            return True
        except Exception as e:
            logger.error(f"Email send failed: {e}")
            return False

    def _layout(self, title: str, body: str) -> str:
        return f"""<!DOCTYPE html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f4f4f5;font-family:Arial,sans-serif">
<div style="max-width:560px;margin:0 auto;padding:24px">
<div style="background:#1e293b;color:white;padding:20px 24px;border-radius:12px 12px 0 0;text-align:center">
<h1 style="margin:0;font-size:20px;font-weight:700">{self.app_name}</h1>
</div>
<div style="background:white;padding:32px 24px;border:1px solid #e2e8f0;border-top:none">
<h2 style="margin:0 0 16px;color:#1e293b;font-size:18px">{title}</h2>
{body}
</div>
<div style="padding:16px 24px;text-align:center;color:#94a3b8;font-size:12px;border:1px solid #e2e8f0;border-top:none;border-radius:0 0 12px 12px;background:#f8fafc">
<p style="margin:0">&copy; {self.app_name}. All rights reserved.</p>
</div>
</div></body></html>"""

    def send_welcome(self, to: str, name: str) -> bool:
        body = f"""<p style="color:#334155;line-height:1.6">Hi <strong>{name}</strong>,</p>
<p style="color:#334155;line-height:1.6">Welcome to {self.app_name}! Your account has been created successfully.</p>
<p style="color:#334155;line-height:1.6">You can now log in and start using the platform.</p>
<p style="color:#94a3b8;font-size:13px;margin-top:24px">If you did not create this account, please ignore this email.</p>"""
        return self._send(to, f"Welcome to {self.app_name}", self._layout("Welcome!", body))

    def send_verification_otp(self, to: str, name: str, otp: str) -> bool:
        body = f"""<p style="color:#334155;line-height:1.6">Hi <strong>{name}</strong>,</p>
<p style="color:#334155;line-height:1.6">Your email verification code is:</p>
<div style="text-align:center;margin:24px 0">
<div style="display:inline-block;background:#f0f9ff;border:2px solid #0ea5e9;border-radius:12px;padding:16px 32px;letter-spacing:8px;font-size:32px;font-weight:800;color:#0c4a6e">{otp}</div>
</div>
<p style="color:#64748b;font-size:13px">This code expires in <strong>10 minutes</strong>. Do not share it with anyone.</p>"""
        return self._send(to, f"Verify Your Email — {self.app_name}", self._layout("Email Verification", body))

    def send_password_reset_otp(self, to: str, name: str, otp: str) -> bool:
        body = f"""<p style="color:#334155;line-height:1.6">Hi <strong>{name}</strong>,</p>
<p style="color:#334155;line-height:1.6">We received a request to reset your password. Your reset code is:</p>
<div style="text-align:center;margin:24px 0">
<div style="display:inline-block;background:#fef2f2;border:2px solid #ef4444;border-radius:12px;padding:16px 32px;letter-spacing:8px;font-size:32px;font-weight:800;color:#991b1b">{otp}</div>
</div>
<p style="color:#64748b;font-size:13px">This code expires in <strong>10 minutes</strong>. If you didn't request this, ignore this email.</p>"""
        return self._send(to, f"Password Reset — {self.app_name}", self._layout("Reset Your Password", body))

    def send_password_changed(self, to: str, name: str) -> bool:
        body = f"""<p style="color:#334155;line-height:1.6">Hi <strong>{name}</strong>,</p>
<p style="color:#334155;line-height:1.6">Your password has been changed successfully.</p>
<p style="color:#ef4444;font-size:13px;margin-top:16px"><strong>If you did not make this change</strong>, please reset your password immediately or contact support.</p>"""
        return self._send(to, f"Password Changed — {self.app_name}", self._layout("Password Updated", body))

    def send_custom(self, to: str, subject: str, message: str) -> bool:
        body = f'<p style="color:#334155;line-height:1.6">{message}</p>'
        return self._send(to, subject, self._layout(subject, body))
