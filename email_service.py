import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from jinja2 import Environment, FileSystemLoader

from config import SMTP_HOST, SMTP_PORT, EMAIL_FROM, GALLERY_BASE_URL, PROJECT_ROOT
from database import get_conn

_jinja_env = Environment(loader=FileSystemLoader(f"{PROJECT_ROOT}/templates"))


def _render_email(guest_name: str, gallery_url: str) -> tuple[str, str]:
    """Returns (plain_text, html) for the notification email."""
    html = _jinja_env.get_template("email_gallery.html").render(
        guest_name=guest_name,
        gallery_url=gallery_url,
    )
    plain = (
        f"Hi {guest_name},\n\n"
        f"Your wedding photos are ready! View them here:\n{gallery_url}\n\n"
        "This gallery is private — only accessible via this link."
    )
    return plain, html


def _send(to_email: str, guest_name: str, gallery_url: str):
    plain, html = _render_email(guest_name, gallery_url)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = "Your wedding photos are ready!"
    msg["From"] = EMAIL_FROM
    msg["To"] = to_email
    msg.attach(MIMEText(plain, "plain"))
    msg.attach(MIMEText(html, "html"))

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as smtp:
        smtp.sendmail(EMAIL_FROM, [to_email], msg.as_string())


def notify_all_unnotified_guests():
    """Send gallery email to every guest who has matches but hasn't been notified yet."""
    with get_conn() as conn:
        guests = conn.execute(
            """
            SELECT DISTINCT g.id, g.name, g.email, g.token
            FROM guests g
            JOIN guest_photo_matches gpm ON gpm.guest_id = g.id
            WHERE g.email_sent = 0
            """
        ).fetchall()

    for guest in guests:
        gallery_url = f"{GALLERY_BASE_URL}/gallery/{guest['token']}"
        try:
            _send(guest["email"], guest["name"], gallery_url)
            with get_conn() as conn:
                conn.execute(
                    "UPDATE guests SET email_sent = 1 WHERE id = ?", (guest["id"],)
                )
            print(f"[email] Sent to {guest['email']}")
        except Exception as e:
            print(f"[email] Failed for {guest['email']}: {e}")
