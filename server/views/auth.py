from flask import Blueprint, request

from schema.others import OAuthCodeArgs

bp = Blueprint("auth", __name__, url_prefix="/auth")


@bp.route("/redirect", methods=["GET"])
def redirect():
    """Endpoint to handle redirection after authentication."""
    code = OAuthCodeArgs.model_validate(request.args.to_dict(), extra="ignore")
    return code.model_dump(mode="json"), 200
