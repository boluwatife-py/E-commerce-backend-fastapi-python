from fastapi import Request
import geoip2.database
from geoip2.errors import AddressNotFoundError
import phonenumbers
import os


reader = geoip2.database.Reader('GeoLite2-Country.mmdb')


def get_country_dial_code(request: Request) -> str:
    """
    Get the dialing code (e.g., +234) based on the request IP address.
    """
    client_ip = request.client.host
    try:
        response = reader.country(client_ip)
        country_code = response.country.iso_code

        dialing_code = phonenumbers.country_code_for_region(country_code)

        return True, f"+{dialing_code}"
    except AddressNotFoundError as e:
        return False, e
    except Exception as e:
        return False, e
