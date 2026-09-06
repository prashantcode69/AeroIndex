import os
import smtplib
from pathlib import Path
from email.mime.text import MIMEText

from dotenv import load_dotenv

# .env Backend/ folder mein hai (mailer.py Backend/pipeline/ mein hai),
# taaki chahe manual run ho, Flask subprocess ho, ya Scheduled Task -
# config hamesha isi file se milegi, alag-alag terminal session ke
# environment variables par depend nahi karna padega.
load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def send_email(to_email, subject, body):
    """
    SMTP config env vars se aata hai:
    SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, ALERT_FROM_EMAIL

    Agar SMTP_USER/SMTP_PASS set nahi hain, actual email send nahi
    hoti - console par log hoke gracefully skip ho jaata hai, taaki
    pipeline kabhi crash na ho sirf isliye ki email abhi configure
    nahi hui.
    """

    smtp_host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(os.environ.get("SMTP_PORT", "587"))
    smtp_user = os.environ.get("SMTP_USER")
    smtp_pass = os.environ.get("SMTP_PASS")
    from_email = os.environ.get("ALERT_FROM_EMAIL") or smtp_user

    if not smtp_user or not smtp_pass:
        print(
            "[mailer] SMTP not configured (set SMTP_USER / SMTP_PASS "
            f"env vars). Would have emailed {to_email}: {subject}"
        )
        return False

    message = MIMEText(body)
    message["Subject"] = subject
    message["From"] = from_email
    message["To"] = to_email

    try:
        with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.sendmail(from_email, [to_email], message.as_string())

        print(f"[mailer] Sent alert email to {to_email}")
        return True

    except Exception as error:
        print(f"[mailer] Failed to send email to {to_email}: {error}")
        return False
