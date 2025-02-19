import httpx
from .config import settings
import requests

def send_otp_sms(phone_number: str, otp: int) -> str:
    """
    Sends an OTP SMS using SMSCountry API.

    :param phone_number: Recipient's phone number (E.164 format e.g., +2348012345678)
    :param otp: The OTP code to be sent (e.g., '123456')
    :return: SMSCountry API response as a string
    :raises: RuntimeError if SMS fails to send
    """
    try:
        params = {
            "User": settings.SMSCOUNTRY_USERNAME,
            "passwd": settings.SMSCOUNTRY_PASSWORD,
            "mobilenumber": phone_number,
            "message": f"Your OTP is {otp}",
            "sid": settings.SMSC_SENDER_ID,
            "mtype": "N",
            "DR": "1",
        }

        with httpx.Client() as client:
            response = client.get(settings.SMSC_URL, params=params)

        if response.status_code != 200 or "failed" in response.text.lower():
            raise RuntimeError(f"Failed to send OTP. Response: {response.text}")

        return response.text

    except httpx.HTTPStatusError as e:
        raise RuntimeError(f"HTTP error while sending OTP: {str(e)}")

    except httpx.RequestError as e:
        raise RuntimeError(f"Network error while sending OTP: {str(e)}")

    except Exception as e:
        raise RuntimeError(f"Unexpected error while sending OTP: {str(e)}")