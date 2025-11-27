import time

import requests
from flask import current_app
from pydantic import TypeAdapter
from pydantic_core import ValidationError
from requests.status_codes import codes

from config import config
from const import MAP_EXIST_EPPN_ENDPOINT

from client.utils import compute_signature

from schema.map_user import MapUser
from schema.map_error import MapError


type ExixtEppnResponse = MapUser | MapError


def exixt_eppn(eppn: str, *, access_token: str, client_secret: str):
    """Check if the given ePPN exists in mAP Core."""
    time_stamp = str(int(time.time()))
    signature = compute_signature(client_secret, access_token, time_stamp)

    try:
        response = requests.get(
            f"{config.MAP_CORE_BASE_URL}{MAP_EXIST_EPPN_ENDPOINT}/{eppn}",
            params={
                "time_stamp": time_stamp,
                "signature": signature,
            },
            headers={
                "Authorization": f"Bearer {access_token}",
            },
            timeout=10,
        )
        # NOTE: if not exists, 400 is returned.
        if codes.bad_request < response.status_code:
            response.raise_for_status()
        data = response.json()
    except requests.RequestException as ex:
        error_type = type(ex).__name__
        current_app.logger.error(
            "Failed to check ePPN existence for %s: %s", eppn, error_type
        )
        raise
    except Exception:
        current_app.logger.error(
            "An unexpected error occurred while checking ePPN existence for %s.", eppn
        )
        raise

    try:
        adaper: TypeAdapter[ExixtEppnResponse] = TypeAdapter(ExixtEppnResponse)
        result = adaper.validate_python(data, extra="ignore")
    except ValidationError:
        current_app.logger.error("Received invalid ePPN existence response.")
        raise

    if isinstance(result, MapError):
        return False, None
    return True, result
