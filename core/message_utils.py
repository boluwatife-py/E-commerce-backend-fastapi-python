from twilio.rest import Client
from .config import settings

def send_otp_sms(phone_number: str, otp: int) -> str:
    """
    Sends an OTP SMS using Twilio API.

    :param phone_number: Recipient's phone number (E.164 format e.g., +2348012345678)
    :param otp: The OTP code to be sent (e.g., '123456')
    :return: Twilio message SID if successful
    :raises: RuntimeError if SMS fails to send
    """
    try:
        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

        message = client.messages.create(
            body=f"Your verification code for {settings.APP_NAME} is: {otp}. This code will expire in 10 minutes. Do not share it with anyone. If you didn't request this, please ignore this message.",
            from_=settings.TWILIO_PHONE_NUMBER,  # Your Twilio number
            to=phone_number
        )

        return message.sid

    except Exception as e:
        raise RuntimeError(f"Failed to send OTP via Twilio: {str(e)}")
