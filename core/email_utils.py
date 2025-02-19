import smtplib
from email.mime.text import MIMEText
from core.config import settings
from email.message import EmailMessage
from pydantic import EmailStr
import time



def send_mail(email: EmailStr, body, subject):
    max_retries = settings.MAX_EMAIL_RETRIES
    retries = 0
    while retries < max_retries:
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
            retries += 1
            time.sleep(3)
            return False, "SMTP server is unavailable"

        except smtplib.SMTPAuthenticationError:
            retries += 1
            time.sleep(3)
            return False, "SMTP authentication failed"

        except Exception as e:
            retries += 1
            time.sleep(3)
            return False, f"Email sending failed: {str(e)}"

def send_verification_email(email: EmailStr, token: str):
    verification_link = f"{settings.BASE_URL}/auth/verify-email?token={token}"
    subject = "Verify Your Email"
    body = f"Click the link to verify your email: {verification_link}\n\nThis link expires in 30 minutes."

    return send_mail(email=email, body=body, subject=subject)

def successful_verified_email(email: EmailStr, name:str):
    subject = "Email Successfully Verified"
    body = f"{name}, Your account have been verified successfully."

    return send_mail(email=email, body=body, subject=subject)

def send_reset_password_email(to_email: EmailStr, reset_token: str):
    subject = "Reset Your Password"
    body = f"Click here to reset your password: {reset_token}"

    return send_mail(email=to_email, body=body, subject=subject)

def successful_upgrade_email_m(to_email: EmailStr, name: str):
    subject = "Successfully upgraded"
    body = f"congratulations {name} You have become a merchant"

    return send_mail(email=to_email, body=body, subject=subject)
