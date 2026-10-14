from app.core.rate_limits import redis_client
from app.core.errors import DomainError
class InAppNotifications:
    async def publish(self,topic,payload):
        # Only identifiers go to transient notifications; full data stays in PostgreSQL.
        try:await redis_client.publish(topic,str(payload))
        except Exception:return
