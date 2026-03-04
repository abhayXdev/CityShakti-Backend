import logging
import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

BREVO_API_KEY = os.getenv("BREVO_API_KEY", "")
BREVO_SENDER_EMAIL = os.getenv("BREVO_SENDER_EMAIL", os.getenv("GMAIL_USER", "jansetu.notifications@gmail.com"))

logger = logging.getLogger(__name__)

# ────────────────────────────────────────────────────
# EMAIL OTP SENDER (Brevo API — Works on Render)
# ────────────────────────────────────────────────────

def send_otp_email(to_email: str, otp_code: str):
    """
    Sends a professional HTML OTP email via Brevo REST API.
    Works on Render because it uses Port 443 (HTTPS), not SMTP.
    """
    if not BREVO_API_KEY:
        # Fallback: Print to console for dev testing if no API key
        print("\n" + "█" * 60)
        print("🚨  BREVO API KEY MISSING: OTP FALLBACK LOG")
        print("█" * 60)
        print(f"  TARGET EMAIL : {to_email}")
        print(f"  OTP CODE     : {otp_code}")
        print("█" * 60 + "\n")
        return True

    url = "https://api.brevo.com/v3/smtp/email"
    
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "api-key": BREVO_API_KEY
    }

    # Professional HTML Body for Brevo
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <body style="font-family: Arial, sans-serif; background-color: #f4f7f6; padding: 20px;">
        <div style="max-width: 600px; margin: auto; background: white; padding: 20px; border-radius: 10px; box-shadow: 0 4px 10px rgba(0,0,0,0.1);">
            <div style="text-align: center; border-bottom: 2px solid #0284c7; padding-bottom: 20px;">
                <h1 style="color: #1a56db; margin: 0;">🏗️ JanSetu</h1>
                <p style="color: #64748b; font-size: 14px; margin: 5px 0 0;">Government of India - Civic Monitoring</p>
            </div>
            <div style="padding: 30px 20px; text-align: center;">
                <p style="font-size: 16px; color: #334155;">Please use the following One-Time Password (OTP) to verify your account:</p>
                <div style="background: #f0f9ff; border: 2px dashed #0284c7; border-radius: 8px; padding: 15px; margin: 20px 0;">
                    <span style="font-size: 32px; font-weight: bold; letter-spacing: 5px; color: #1e40af;">{otp_code}</span>
                </div>
                <p style="font-size: 14px; color: #64748b;">This code will expire in 5 minutes. Please do not share this code with anyone.</p>
            </div>
            <div style="text-align: center; font-size: 12px; color: #94a3b8; border-top: 1px solid #e2e8f0; padding-top: 20px;">
                © 2026 JanSetu. All rights reserved. <br>
                Secured by National Informatics Centre (NIC)
            </div>
        </div>
    </body>
    </html>
    """

    payload = {
        "sender": {"name": "JanSetu Support", "email": BREVO_SENDER_EMAIL},
        "to": [{"email": to_email}],
        "subject": "🔐 Your JanSetu Verification Code",
        "htmlContent": html_content
    }

    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=15)
        if response.status_code in [201, 200, 202]:
            logger.info(f"OTP email sent successfully to {to_email} via Brevo")
            return True
        else:
            logger.error(f"Brevo API Error: {response.text}")
            # Fallback to logs if API fails
            raise Exception(f"Brevo API returned {response.status_code}")
            
    except Exception as e:
        logger.warning(f"Brevo API failed: {e}")
        # FALLBACK: Print to Render console so developer can still see it
        print("\n" + "█" * 60)
        print("🚨  BREVO API FAILED: OTP FALLBACK LOG")
        print("█" * 60)
        print(f"  TARGET EMAIL : {to_email}")
        print(f"  OTP CODE     : {otp_code}")
        print(f"  ERROR        : {str(e)}")
        print("█" * 60 + "\n")
        return True




# ─────────────────────────────────────────────────────────
# SMS TEMPLATES
# ─────────────────────────────────────────────────────────

def _sms_body(event: str, title: str, extra: str = "") -> str:
    templates = {
        "registered":   f"[JanSetu] Your complaint '{title}' has been successfully registered. Ticket ID will be shared shortly. -NIC",
        "in_progress":  f"[JanSetu] UPDATE: Your complaint '{title}' is now IN PROGRESS. Our team is actively working on it. -NIC",
        "assigned":     f"[JanSetu] UPDATE: Your complaint '{title}' has been ASSIGNED to the relevant department. -NIC",
        "resolved":     f"[JanSetu] Your complaint '{title}' has been RESOLVED. Please verify and close the ticket on JanSetu. -NIC",
        "closed":       f"[JanSetu] Thank you! Your complaint '{title}' has been CLOSED. We value your feedback. -NIC",
        "rejected":     f"[JanSetu] ALERT: Your rejection was received. Ticket '{title}' re-escalated to Priority {extra}. Officers notified. -NIC",
        "generic":      f"[JanSetu] Status update for '{title}': {extra}. Visit JanSetu for details. -NIC",
    }
    return templates.get(event, templates["generic"])


def send_sms(phone: str, message: str, event: str = "generic", title: str = "", extra: str = ""):
    """
    Simulation Mode: Print the SMS to the backend terminal log.
    In production, replace this with a Twilio / MSG91 API call.
    If `event` and `title` are provided, uses a structured template.
    Otherwise uses the raw `message` string.
    """
    body = _sms_body(event, title, extra) if (event != "generic" or title) else message

    print("\n" + "═" * 55)
    print("📱  JanSetu SMS NOTIFICATION")
    print("═" * 55)
    print(f"  To      : +91 {phone}")
    print("  From    : JanSetu (VMID: NIC-JANSETU)")
    print(f"  Message : {body}")
    print("═" * 55 + "\n")


# ─────────────────────────────────────────────────────────
# EMAIL TEMPLATES (HTML)
# ─────────────────────────────────────────────────────────

def _email_html(subject: str, citizen_name: str, body_lines: list[str]) -> str:
    body_html = "".join(f"<p style='margin:6px 0;color:#374151;'>{line}</p>" for line in body_lines)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>{subject}</title>
</head>
<body style="margin:0;padding:0;background:#f3f4f6;font-family:Arial,Helvetica,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f3f4f6;padding:32px 0;">
    <tr>
      <td align="center">
        <table width="600" cellpadding="0" cellspacing="0"
               style="background:#ffffff;border-radius:12px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.08);">

          <!-- HEADER -->
          <tr>
            <td style="background:linear-gradient(135deg,#1a56db,#0284c7);padding:28px 36px;text-align:center;">
              <h1 style="margin:0;color:#ffffff;font-size:22px;letter-spacing:0.5px;">🏛️ JanSetu</h1>
              <p style="margin:4px 0 0;color:#bfdbfe;font-size:13px;">Smart Civic Monitoring System — Government of India</p>
            </td>
          </tr>

          <!-- BODY -->
          <tr>
            <td style="padding:32px 36px;">
              <p style="font-size:15px;color:#111827;font-weight:600;">Dear {citizen_name},</p>
              {body_html}
            </td>
          </tr>

          <!-- DIVIDER -->
          <tr>
            <td style="padding:0 36px;">
              <hr style="border:none;border-top:1px solid #e5e7eb;" />
            </td>
          </tr>

          <!-- FOOTER -->
          <tr>
            <td style="padding:20px 36px;text-align:center;">
              <p style="font-size:11px;color:#9ca3af;margin:0;">
                This is an automated notification from JanSetu.<br/>
                Do <strong>not</strong> reply to this email.<br/>
                Secured &amp; operated by <strong>National Informatics Centre (NIC)</strong>
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


STATUS_EMAIL_BODIES = {
    "registered": lambda title: [
        f"Your complaint <strong>'{title}'</strong> has been <span style='color:#2563eb;font-weight:700;'>successfully registered</span> in the JanSetu portal.",
        "Our AI system is currently categorizing your report and assigning it to the relevant department.",
        "You will receive further notifications as its status progresses.",
        "<br/><em>Please note your Ticket ID from the JanSetu app for future reference.</em>",
    ],
    "in_progress": lambda title: [
        f"Great news! Your complaint <strong>'{title}'</strong> is now <span style='color:#d97706;font-weight:700;'>IN PROGRESS</span>.",
        "A member of the relevant department is actively working on resolving this issue.",
        "You will be notified again once it is marked as Resolved.",
    ],
    "assigned": lambda title: [
        f"Your complaint <strong>'{title}'</strong> has been <span style='color:#7c3aed;font-weight:700;'>ASSIGNED</span> to the appropriate officer.",
        "Work will begin shortly. You can track live progress in your JanSetu dashboard.",
    ],
    "resolved": lambda title: [
        f"Your complaint <strong>'{title}'</strong> has been marked as <span style='color:#059669;font-weight:700;'>RESOLVED</span> by the assigned officer.",
        "Please open your JanSetu portal and verify if the issue has been fixed to your satisfaction.",
        "You may click <strong>Verify &amp; Close</strong> to confirm, or <strong>Reject &amp; Re-Escalate</strong> if the problem persists.",
    ],
    "closed": lambda title: [
        f"Your complaint <strong>'{title}'</strong> has been officially <span style='color:#16a34a;font-weight:700;'>CLOSED</span>.",
        "Thank you for using JanSetu and helping us build a smarter, cleaner civic environment.",
        "Your feedback matters. You may rate the resolution from within the JanSetu app.",
    ],
    "rejected": lambda title: [
        f"We acknowledge your rejection of the resolution for <strong>'{title}'</strong>.",
        "The ticket has been <span style='color:#dc2626;font-weight:700;'>RE-ESCALATED</span> with a higher priority level.",
        "Officers have been notified and are expected to respond with urgency.",
        "We apologize for the inconvenience and assure you of prompt action.",
    ],
}


def send_email(
    email: str,
    subject: str,
    message: str,
    event: str = "generic",
    title: str = "",
    citizen_name: str = "Citizen",
):
    """
    Simulation Mode: Print a formatted HTML email to the backend terminal log.
    In production, replace this with SendGrid / Resend / SMTP.
    """
    if event in STATUS_EMAIL_BODIES and title:
        body_lines = STATUS_EMAIL_BODIES[event](title)
    else:
        body_lines = [line for line in message.split("\n") if line.strip()]

    html = _email_html(subject, citizen_name, body_lines)

    print("\n" + "═" * 70)
    print("📧  JanSetu EMAIL DISPATCHED")
    print("═" * 70)
    print(f"  To      : {email}")
    print("  From    : no-reply@jansetu.gov.in")
    print(f"  Subject : {subject}")
    print("  " + "─" * 66)
    print("  [HTML BODY PREVIEW]")
    for line in body_lines:
        clean = line.replace("<strong>", "**").replace("</strong>", "**") \
                    .replace("<br/>", "").replace("<em>", "_").replace("</em>", "_")
        import re
        clean = re.sub(r"<[^>]+>", "", clean)
        print(f"  | {clean}")
    print("  " + "─" * 66)
    print("  | This is an automated notification. Do not reply.")
    print("  | Secured by National Informatics Centre (NIC)")
    print("═" * 70 + "\n")
