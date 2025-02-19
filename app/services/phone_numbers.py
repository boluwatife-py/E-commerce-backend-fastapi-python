import phonenumbers
from phonenumbers import geocoder

def get_country_from_phone_number(phone_number: str):
    try:
        parsed_number = phonenumbers.parse(phone_number)
        country = geocoder.description_for_number(parsed_number, "en")  # 'en' for English
        return country
    except phonenumbers.NumberParseException:
        return "Invalid phone number"
