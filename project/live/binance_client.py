from __future__ import annotations

import hmac
import hashlib
import time
import logging
import aiohttp
from typing import Any, Dict, List, Optional
from urllib.parse import urlencode

_LOG = logging.getLogger(__name__)

class BinanceFuturesClient:
    """
    Binance USD-M Futures REST Client using aiohttp.
    """
    BASE_URL = "https://fapi.binance.com"

    def __init__(self, api_key: str, api_secret: str):
        self.api_key = api_key
        self.api_secret = api_secret

    def _sign(self, params: Dict[str, Any]) -> str:
        query_string = urlencode(params)
        return hmac.new(
            self.api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

    async def _request(self, method: str, path: str, params: Dict[str, Any] = None, signed: bool = False) -> Any:
        params = params or {}
        if signed:
            params["timestamp"] = int(time.time() * 1000)
            params["signature"] = self._sign(params)

        headers = {"X-MBX-APIKEY": self.api_key}
        url = f"{self.BASE_URL}{path}"

        async with aiohttp.ClientSession() as session:
            async with session.request(method, url, params=params, headers=headers) as resp:
                data = await resp.json()
                if resp.status != 200:
                    _LOG.error(f"Binance API Error: {resp.status} {data}")
                    resp.raise_for_status()
                return data

    async def get_account_v2(self) -> Dict[str, Any]:
        """GET /fapi/v2/account"""
        return await self._request("GET", "/fapi/v2/account", signed=True)

    async def cancel_all_open_orders(self, symbol: str) -> Any:
        """DELETE /fapi/v1/allOpenOrders"""
        return await self._request("DELETE", "/fapi/v1/allOpenOrders", params={"symbol": symbol.upper()}, signed=True)

    async def create_market_order(self, symbol: str, side: str, quantity: float, reduce_only: bool = False) -> Any:
        """POST /fapi/v1/order"""
        params = {
            "symbol": symbol.upper(),
            "side": side.upper(),
            "type": "MARKET",
            "quantity": quantity,
            "reduceOnly": "true" if reduce_only else "false"
        }
        return await self._request("POST", "/fapi/v1/order", params=params, signed=True)
