import json
import flet as ft

@ft.control("IronCycleBilling")
class IronCycleBilling(ft.Service):
    """Privacy-safe Google Play Billing bridge for IronCycle."""
    async def _call(self, name: str, args=None) -> dict:
        raw = await self._invoke_method(name, args or {})
        return json.loads(raw) if isinstance(raw, str) else (raw or {})

    async def is_available(self) -> bool:
        return bool(await self._invoke_method("is_available"))

    async def query_product(self, product_id: str) -> dict:
        return await self._call("query_product", {"product_id": product_id})

    async def purchase(self, product_id: str) -> dict:
        return await self._call("purchase", {"product_id": product_id})

    async def restore(self, product_id: str) -> dict:
        return await self._call("restore", {"product_id": product_id})

    async def reconcile(self, product_id: str) -> dict:
        """Quietly reconcile ownership; inconclusive results never mean revocation."""
        return await self._call("reconcile", {"product_id": product_id})

    async def take_event(self) -> dict:
        """Return and clear the latest privacy-safe purchase-stream event."""
        return await self._call("take_event")
