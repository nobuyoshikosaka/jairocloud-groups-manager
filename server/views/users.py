import traceback

from flask import Blueprint, jsonify, request

from client.users import exixt_eppn
from services.service_settings import get_access_token, get_client_cert

bp = Blueprint("users", __name__, url_prefix="/api/users")


@bp.route("/exist", methods=["GET"])
def exist():
    """Endpoint to check if a given ePPN exists in mAP Core."""
    eppn = request.args.get("eppn")
    if not eppn:
        return jsonify(error="Missing eppn parameter."), 400

    token = get_access_token()
    cert = get_client_cert()
    if not token or not cert:
        return jsonify(error="Service not authenticated."), 401

    try:
        exists = exixt_eppn(
            eppn,
            access_token=token.access_token,
            client_secret=cert.client_secret,
        )
    except Exception as e:
        traceback.print_exc()
        return jsonify(error=str(e)), 500

    if exists[0] is False:
        return jsonify(exists=False), 200
    return jsonify(
        exists=exists[0],
        user=exists[1].model_dump(mode="json", by_alias=True),
    ), 200
