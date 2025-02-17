import smtplib
from email.mime.text import MIMEText
from core.config import settings
from email.message import EmailMessage


def send_verification_email(email: str, token: str):
    verification_link = f"{settings.BASE_URL}/auth/verify-email?token={token}"
    subject = "Verify Your Email"
    body = f"Click the link to verify your email: {verification_link}\n\nThis link expires in 30 minutes."

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = settings.SMTP_USERNAME
    msg["To"] = email

    try:
        with smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT) as server:
            # server.starttls()
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.sendmail(settings.SMTP_USERNAME, email, msg.as_string())
            return True, "Email sent successfully"

            
    except smtplib.SMTPConnectError:
        return False, "SMTP server is unavailable"

    except smtplib.SMTPAuthenticationError:
        return False, "SMTP authentication failed"

    except Exception as e:
        return False, f"Email sending failed: {str(e)}"


def send_reset_password_email(to_email, reset_token):
    msg = EmailMessage()
    msg["Subject"] = "Reset Your Password"
    msg["From"] = settings.SMTP_USERNAME
    msg["To"] = to_email
    msg.set_content(f"Click here to reset your password: {reset_token}")

    try:
        with smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT, timeout=10) as server:
            # server.starttls()
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.send_message(msg)
        return True, "Email sent successfully"
    
    except smtplib.SMTPConnectError:
        return False, "SMTP server is unavailable"

    except smtplib.SMTPAuthenticationError:
        return False, "SMTP authentication failed"

    except Exception as e:
        return False, f"Email sending failed: {str(e)}"



def successful_upgrade_email_m(to_email, name):
    msg = EmailMessage()
    msg["Subject"] = "Successfully upgraded"
    msg["From"] = settings.SMTP_USERNAME
    msg["To"] = to_email
    msg.set_content(f"congratulations {name} You have become a merchant")

    try:
        with smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT, timeout=10) as server:
            # server.starttls()
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.send_message(msg)
        return True, "Email sent successfully"
    
    except smtplib.SMTPConnectError:
        return False, "SMTP server is unavailable"

    except smtplib.SMTPAuthenticationError:
        return False, "SMTP authentication failed"

    except Exception as e:
        return False, f"Email sending failed: {str(e)}"