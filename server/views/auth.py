import requests
from flask import Blueprint, current_app, redirect, request, url_for

from client.oauth import issue_certificate, get_access_token
from config import config
from const import MAP_OAUTH_AUTHORIZE_ENDPOINT
from services.service_settings import get_client_cert, set_client_cert, set_access_token
from schema.others import OAuthCodeArgs

bp = Blueprint("auth", __name__, url_prefix="/api/auth")


@bp.route("/issue_cert", methods=["GET"])
def issue_cert():
    """Endpoint to issue a client certificate."""
    entity_id = request.args.get("entity_id")
    if not entity_id:
        return {"error": "Missing entity_id parameter."}, 400
    cert = issue_certificate(entity_id)
    set_client_cert(cert)

    redirect_url = url_for("auth.callback", _external=True)
    auth_request_url = (
        requests.Request(
            "GET",
            f"{config.MAP_CORE_BASE_URL}{MAP_OAUTH_AUTHORIZE_ENDPOINT}",
            params={
                "response_type": "code",
                "client_id": cert.client_id,
                "redirect_uri": redirect_url,
                "state": entity_id,
            },
        )
        .prepare()
        .url
    )

    if auth_request_url is None:
        current_app.logger.error("Failed to prepare auth request URL.")
        return {"error": "Internal server error."}, 500

    current_app.logger.info("Redirecting to %s", auth_request_url)
    return redirect(auth_request_url)


@bp.route("/callback", methods=["GET"])
def callback():
    """Endpoint to handle redirection after authentication."""
    code = OAuthCodeArgs.model_validate(request.args.to_dict(), extra="ignore")
    cert = get_client_cert()
    if not code or not cert:
        return {"error": "Invalid request parameters."}, 400

    access_token = get_access_token(code, cert)
    set_access_token(access_token)

    return access_token.model_dump(mode="json"), 200
