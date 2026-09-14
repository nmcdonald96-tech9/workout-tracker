import json
import flet as ft


@ft.control("IronCycleBilling")
class IronCycleBilling(ft.Service):
    """Google Play Billing bridge for IronCycle's non-consumable unlock."""

    async def is_available(self) -> bool:
        return bool(await self._invoke_method("is_available"))

    async def query_product(self, product_id: str) -> dict:
        raw = await self._invoke_method("query_product", {"product_id": product_id})
        return json.loads(raw) if isinstance(raw, str) else (raw or {})

    async def purchase(self, product_id: str) -> dict:
        raw = await self._invoke_method("purchase", {"product_id": product_id})
        return json.loads(raw) if isinstance(raw, str) else (raw or {})

    async def restore(self, product_id: str) -> dict:
        raw = await self._invoke_method("restore", {"product_id": product_id})
        return json.loads(raw) if isinstance(raw, str) else (raw or {})
