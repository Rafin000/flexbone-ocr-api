"""Health namespace: liveness check."""
from flask_restx import Namespace, Resource

health_ns = Namespace("health", description="Service health", path="/")


@health_ns.route("/alive")
class Alive(Resource):
    def get(self):
        """Liveness/health check."""
        return {"status": "alive"}
