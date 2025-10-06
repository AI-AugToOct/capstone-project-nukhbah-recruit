# src/email_notifier.py
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import json
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def notify_candidates_by_email(json_path: str, quiz_link: str, sender_email: str, sender_password: str):
    """
    Reads qualified candidates from JSON and sends each an email with a quiz link.
    """
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            candidates = json.load(f)
    except Exception as e:
        logger.error(f"❌ Failed to read candidates file: {e}")
        return

    if not isinstance(candidates, list) or not candidates:
        logger.warning("⚠️ No qualified candidates found in JSON.")
        return

    smtp_server = "smtp.gmail.com"
    smtp_port = 587

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, sender_password)

            for c in candidates:
                email = c.get("email")
                name = c.get("full_name", "Candidate")
                score = c.get("similarity_score", 0)

                if not email:
                    continue

                msg = MIMEMultipart("alternative")
                msg["Subject"] = "🎯 Nukhbah Technical Assessment Invitation"
                msg["From"] = sender_email
                msg["To"] = email

                html_body = f"""
                <html>
                  <body style="font-family:Arial,sans-serif; color:#111;">
                    <p>Dear <b>{name}</b>,</p>
                    <p>Congratulations! Based on your profile similarity score (<b>{score:.2f}</b>), 
                    you have been shortlisted for the next step in our hiring process.</p>
                    <p>Please complete your technical assessment using the link below:</p>
                    <p style="text-align:center; margin:24px 0;">
                      <a href="{quiz_link}" 
                         style="background-color:#22d3ee;color:#000;padding:12px 20px;
                                border-radius:8px;text-decoration:none;font-weight:bold;">
                         Take the Assessment
                      </a>
                    </p>
                    <p>Best regards,<br><b>Nukhbah Recruitment Team</b></p>
                  </body>
                </html>
                """

                msg.attach(MIMEText(html_body, "html"))

                try:
                    server.sendmail(sender_email, email, msg.as_string())
                    logger.info(f"✅ Email sent to {email} ({score:.2f})")
                except Exception as e:
                    logger.warning(f"❌ Failed to send email to {email}: {e}")

    except Exception as e:
        logger.error(f"SMTP connection failed: {e}")
