# providers/changenow.py

import json
import requests
from providers.base import SwapProvider


class ChangeNOWProvider(SwapProvider):
    """
    ChangeNOW swap provider adapter.

    IMPORTANT:
    - Implements SwapProvider exactly
    - No engine logic
    - No lifecycle mutation
    """

    name = "changenow"
    BASE_URL = "https://api.changenow.io/v2"

    def __init__(self, api_key: str):
        self.api_key = api_key

    def _headers(self):
        return {"x-changenow-api-key": self.api_key}

    # -----------------------------------------------------------
    # QUOTE
    # -----------------------------------------------------------

    def get_quote(self, from_coin, to_coin, amount):
        """
        Call ChangeNOW v2 exchange estimated-amount endpoint.
        READ-ONLY: no funds move here.
        """
        url = f"{self.BASE_URL}/exchange/estimated-amount"
        params = {
            "fromCurrency": from_coin.lower(),
            "toCurrency": to_coin.lower(),
            "fromNetwork": from_coin.lower(),
            "toNetwork": to_coin.lower(),
            "fromAmount": amount,
            "flow": "standard",
            "type": "direct",
        }
        response = requests.get(url, headers=self._headers(), params=params, timeout=10)
        # if not response.ok:
        #     raise RuntimeError(
        #         f"ChangeNOW API error {response.status_code}: {response.text}"
        # #     )
        
        # if not response.ok:
        #     try:
        #         err = response.json()
        #         msg = err.get("message", "Unknown error")
        #     except Exception:
        #         msg = response.text
        #     raise RuntimeError(f"ChangeNOW: {msg}")
            
            
        if not response.ok:
            try:
                err = response.json()
                msg = err.get("message", "Unknown error")
                min_amt = err.get("payload", {}).get("range", {}).get("minAmount")
                if min_amt:
                    msg = f"Minimum: {min_amt} {from_coin.upper()}"
            except Exception:
                msg = response.text
            raise RuntimeError(f"{msg}")
            
        data = response.json()
        return {
            "provider": self.name,
            "output_amount": float(data.get("toAmount", 0)),
            "fee": 0.0,
            "meta": {
                "from_coin": from_coin.upper(),
                "to_coin": to_coin.upper(),
                "from_amount": amount,
                "rate_type": "floating",
                "rate": data.get("rate"),
                "min_amount": data.get("minAmount"),
                "max_amount": data.get("maxAmount"),
            },
        }

    # -----------------------------------------------------------
    # CREATE SWAP
    # -----------------------------------------------------------

    def create_swap(self, swap):
        """
        Call POST /v2/exchange to create a real swap with ChangeNOW.
        refundAddress is sent as empty string — optional for standard flow.
        Returns provider metadata ONLY. Must NOT mutate swap state.
        """
        url = f"{self.BASE_URL}/exchange"
        payload = {
            "fromCurrency": swap.from_coin.lower(),
            "toCurrency": swap.to_coin.lower(),
            "fromNetwork": swap.from_coin.lower(),
            "toNetwork": swap.to_coin.lower(),
            "fromAmount": str(swap.amount),
            "toAmount": "",
            "address": swap.receive_address,
            "extraId": "",
            "refundAddress": swap.refund_address or "",
            "refundExtraId": "",
            "userId": "",
            "payload": "",
            # "contactEmail": swap.email or "",
            "contactEmail": "" if swap.refund_address else (swap.email or ""),
            "source": "",
            "flow": "standard",
            "type": "direct",
            "rateId": "",
        }
        response = requests.post(
            url,
            headers={**self._headers(), "Content-Type": "application/json"},
            data=json.dumps(payload),
            timeout=15,
        )
        if not response.ok:
            raise RuntimeError(
                f"ChangeNOW create_swap error {response.status_code}: {response.text}"
            )
        data = response.json()
        provider_execution_id = data.get("id")
        deposit_address = data.get("payinAddress")
        if not provider_execution_id or not deposit_address:
            raise RuntimeError(
                f"ChangeNOW create_swap missing fields in response: {data}"
            )
        print(
            f"[ChangeNOW] swap created — id={provider_execution_id} "
            f"deposit_address={deposit_address}"
        )
        return {
            "provider": self.name,
            "provider_execution_id": provider_execution_id,
            "deposit_address": deposit_address,
        }

    # -----------------------------------------------------------
    # STATUS
    # -----------------------------------------------------------

    def get_status(self, swap):
        """
        Call GET /v2/exchange/by-id?id=<provider_execution_id>.

        ChangeNOW status → engine fact mapping:
          confirming            → "deposit"
          waiting               → None  (no fact yet)
          exchanging / sending  → "swapping"
          finished              → "payout_confirmed"
          failed                → "failed"
          hold                  → "hold"
          other                 →  None  (logged as unknown)      
        """
        swap_id = swap["id"]

        # Retrieve provider_execution_id from the execution_started fact source JSON
        from engine_helpers.db_utils import get_db
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT source FROM facts WHERE swap_id = ? AND fact_type = ?",
            (swap_id, "execution_started")
        )
        row = cursor.fetchone()
        conn.close()

        if row is None:
            print(f"[ChangeNOW] no execution_started fact for swap {swap_id}")
            return None

        try:
            source_data = json.loads(row["source"])
            provider_execution_id = source_data.get("provider_execution_id")
        except (json.JSONDecodeError, TypeError):
            print(f"[ChangeNOW] could not parse source JSON for swap {swap_id}")
            return None

        if not provider_execution_id:
            print(f"[ChangeNOW] no provider_execution_id for swap {swap_id}")
            return None

        # Call ChangeNOW
        url = f"{self.BASE_URL}/exchange/by-id"
        try:
            response = requests.get(
                url,
                headers=self._headers(),
                params={"id": provider_execution_id},
                timeout=10,
            )
        except requests.RequestException as e:
            print(f"[ChangeNOW] get_status network error for swap {swap_id}: {e}")
            return None

        if not response.ok:
            print(
                f"[ChangeNOW] get_status error {response.status_code} "
                f"for swap {swap_id}: {response.text}"
            )
            return None

        data = response.json()
        cn_status = data.get("status", "")
        if cn_status != "waiting":
            print(f"[ChangeNOW] swap {swap_id} provider_status={cn_status}")
# deposit detected too early bug fix 08-july-26
        # if cn_status in ("waiting", "confirming"):
            
        if cn_status == "confirming":
            return "deposit"
        elif cn_status in ("exchanging", "sending"):
            return "swapping"
        elif cn_status == "finished":
            return "payout_confirmed"
        elif cn_status == "waiting":
            return None  # still waiting for user deposit — normal, no fact yet
        elif cn_status == "hold":
            print(f"[ChangeNOW] swap {swap_id} is on hold — manual review required")
            return "hold"
        elif cn_status == "failed":
            print(f"[ChangeNOW] swap {swap_id} reported failed by provider")
            return "failed"
        else:
            print(f"[ChangeNOW] swap {swap_id} unknown status: {cn_status}")
            return None

