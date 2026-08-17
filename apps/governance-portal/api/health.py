from flask.views import MethodView
import marshmallow as ma
from flask_smorest import Blueprint


blp_health = Blueprint(
    "health",
    __name__,
    url_prefix="/api/v1",
    description="Governance Portal health operations",
)


class HealthSchema(ma.Schema):
    """
    Response schema for the health endpoint.
    """

    status = ma.fields.String(
        required=True
    )

    application = ma.fields.String(
        required=True
    )


@blp_health.route("/health")
class HealthResource(MethodView):

    @blp_health.response(
        200,
        HealthSchema,
    )
    def get(self):
        """
        Check Governance Portal availability.
        """
        return {
            "status": "ok",
            "application": (
                "NovaSecure IAM Governance Portal"
            ),
        }