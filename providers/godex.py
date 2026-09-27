# providers/godex.py

import json
import requests
from providers.base import SwapProvider


class GodexProvider(SwapProvider):
    """
    Godex.io swap provider adapter.

    No KYC required. Fixed rate option available.
    API docs: https://api.godex.io/api

    IMPORTANT:
    - Implements SwapProvider exactly
    - No engine logic
    - No lifecycle mutation
    """

    name = "godex"
    BASE_URL = "https://api.godex.io/api/v1"

    def __init__(self, api_key: str, affiliate_id: str = ""):
        self.api_key = api_key
        self.affiliate_id = affiliate_id  # optional but earns commission

    def _headers(self):
        return {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "public-key": self.api_key,
        }

    # -----------------------------------------------------------
    # QUOTE  (POST /api/v1/info)
    # -----------------------------------------------------------

    def get_quote(self, from_coin, to_coin, amount):
        """
        Get a floating-rate quote from Godex.
        Uses POST /api/v1/info — returns estimated output amount.
        Coins must be uppercase tickers: LTC, XMR, BTC, ETH etc.
        """
        url = f"{self.BASE_URL}/info"
        payload = {
            "from": from_coin.upper(),
            "to": to_coin.upper(),
            "amount": amount,
            "float": True,          # floating rate
            "network_from": from_coin.upper(),
            "network_to": to_coin.upper(),
        }

        response = requests.post(
            url,
            headers=self._headers(),
            data=json.dumps(payload),
            timeout=10,
        )

        if not response.ok:
            raise RuntimeError(
                f"Godex get_quote error {response.status_code}: {response.text}"
            )

        data = response.json()

        output_amount = float(data.get("amount", 0))
        min_amount = data.get("min_amount")
        max_amount = data.get("max_amount")
        rate = data.get("rate")

        return {
            "provider": self.name,
            "output_amount": output_amount,
            "fee": float(data.get("fee", 0)),
            "meta": {
                "from_coin": from_coin.upper(),
                "to_coin": to_coin.upper(),
                "from_amount": amount,
                "rate_type": "floating",
                "rate": rate,
                "min_amount": min_amount,
                "max_amount": max_amount,
                "rate_uuid": data.get("rate_uuid"),
            },
        }

    # -----------------------------------------------------------
    # CREATE SWAP  (POST /api/v1/transaction)
    # -----------------------------------------------------------

    def create_swap(self, swap):
        """
        Create a real swap transaction with Godex.
        Returns provider metadata ONLY. Must NOT mutate swap state.

        Key fields returned by Godex:
          transaction_id  → our provider_execution_id
          deposit         → the address user sends coins to
        """
        url = f"{self.BASE_URL}/transaction"
        payload = {
            "coin_from": swap.from_coin.upper(),
            "coin_to": swap.to_coin.upper(),
            "deposit_amount": str(swap.amount),
            "withdrawal": swap.receive_address,   # where user receives funds
            "withdrawal_extra_id": "",             # not needed for LTC/XMR/BTC/ETH
            "return": "",                          # optional refund address
            "return": swap.refund_address or "",   # optional refund address
            "return_extra_id": "",
            "float": True,                         # floating rate
            "coin_from_network": swap.from_coin.upper(),
            "coin_to_network": swap.to_coin.upper(),
        }

        # Include affiliate_id if set — earns commission on every swap
        if self.affiliate_id:
            payload["affiliate_id"] = self.affiliate_id

        response = requests.post(
            url,
            headers=self._headers(),
            data=json.dumps(payload),
            timeout=15,
        )

        if not response.ok:
            raise RuntimeError(
                f"Godex create_swap error {response.status_code}: {response.text}"
            )

        data = response.json()

        provider_execution_id = data.get("transaction_id")
        deposit_address = data.get("deposit")

        if not provider_execution_id or not deposit_address:
            raise RuntimeError(
                f"Godex create_swap missing fields in response: {data}"
            )

        print(
            f"[Godex] swap created — id={provider_execution_id} "
            f"deposit_address={deposit_address}"
        )

        return {
            "provider": self.name,
            "provider_execution_id": provider_execution_id,
            "deposit_address": deposit_address,
        }

    # -----------------------------------------------------------
    # GET STATUS  (GET /api/v1/transaction/{id}/status)
    # -----------------------------------------------------------

    # def get_status(self, swap):
    #     """
    #     Poll GET /api/v1/transaction/{id}/status for current status.

    #     Godex status → engine fact mapping:
    #       wait                                  → "deposit"  (waiting, show deposit address)
    #       confirmation / confirmed              → "deposit"  (deposit seen, confirming)
    #       exchanging / sending / sending_confirmation → "swapping"
    #       success                               → "payout_confirmed"
    #       overdue / error / refunded            → None  (engine handles via timeout)
    #     """
    #     swap_id = swap["id"]

    #     # Get provider_execution_id from the execution_started fact
    #     from engine_helpers.db_utils import get_db
    #     conn = get_db()
    #     cursor = conn.cursor()
    #     cursor.execute(
    #         "SELECT source FROM facts WHERE swap_id = ? AND fact_type = ?",
    #         (swap_id, "execution_started")
    #     )
    #     row = cursor.fetchone()
    #     conn.close()

    #     if row is None:
    #         print(f"[Godex] no execution_started fact for swap {swap_id}")
    #         return None

    #     # try:
    #     #     source_data = json.loads(row["source"])
    #     #     provider_execution_id = source_data.get("provider_execution_id")
    #     # except (json.JSONDecodeError, TypeError):
    #     #     print(f"[Godex] could not parse source JSON for swap {swap_id}")
    #     #     return None
        
        

    #     # if not provider_execution_id:
    #     #     print(f"[Godex] no provider_execution_id for swap {swap_id}")
    #     #     return None
        
    #     try:
    #         data = response.json()
    #         godex_status = data.get("status", "").strip()
    #     except (json.JSONDecodeError, ValueError):
    #         godex_status = response.text.strip().strip('"')

    #     if not godex_status:
    #         # Empty response — old bug may have resurfaced, treat silently as None
    #         print(f"[Godex] swap {swap_id} empty status response")
    #         return None



    #     # Try JSON first (in case Godex fix their Content-Type), fall back to plain text

    #     # Call Godex status endpoint
    #     url = f"{self.BASE_URL}/transaction/{provider_execution_id}/status"
    #     try:
    #         response = requests.get(
    #             url,
    #             headers=self._headers(),
    #             timeout=10,
    #         )
    #     except requests.RequestException as e:
    #         print(f"[Godex] get_status network error for swap {swap_id}: {e}")
    #         return None

    #     if not response.ok:
    #         print(
    #             f"[Godex] get_status error {response.status_code} "
    #             f"for swap {swap_id}: {response.text}"
    #         )
    #         return None

    #     # Godex returns the status as a plain string
    #     godex_status = response.text.strip().strip('"')
    #     print(f"[Godex] swap {swap_id} provider_status={godex_status}")

    #     if godex_status in ("wait",):
    #         # Still waiting for deposit — no fact needed yet, just return None
    #         # The deposit fact will be inserted when confirmation begins
    #         return None

    #     elif godex_status in ("confirmation", "confirmed"):
    #         return "deposit"

    #     elif godex_status in ("exchanging", "sending", "sending_confirmation"):
    #         return "swapping"

    #     elif godex_status == "success":
    #         return "payout_confirmed"

    #     # elif godex_status in ("overdue", "error", "refunded"):
    #     #     print(f"[Godex] swap {swap_id} terminal status: {godex_status}")
    #     #     return None
        
    #     elif godex_status in ("overdue", "error", "refunded"):
    #         print(f"[Godex] swap {swap_id} terminal status: {godex_status}")
    #         return "failed"

    #     else:
    #         print(f"[Godex] swap {swap_id} unknown status: {godex_status}")
    #         return None
        
        
    def get_status(self, swap):
        """
        Poll GET /api/v1/transaction/{id}/status for current status.
    
        Godex status → engine fact mapping:
          wait                                        → None     (waiting for deposit, no change)
          confirmation / confirmed                    → "deposit"
          exchanging / sending / sending_confirmation → "swapping"
          success                                     → "payout_confirmed"
          overdue / error / refunded                  → "failed"
        """
        swap_id = swap["id"]

    # Get provider_execution_id from the execution_started fact
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
            print(f"[Godex] no execution_started fact for swap {swap_id}")
            return None
    
        try:
            source_data = json.loads(row["source"])
            provider_execution_id = source_data.get("provider_execution_id")
        except (json.JSONDecodeError, TypeError):
            print(f"[Godex] could not parse source JSON for swap {swap_id}")
            return None
    
        if not provider_execution_id:
            print(f"[Godex] no provider_execution_id for swap {swap_id}")
            return None

    # Call Godex status endpoint
        url = f"{self.BASE_URL}/transaction/{provider_execution_id}/status"
        try:
            response = requests.get(
                url,
                headers=self._headers(),
                timeout=10,
            )
        except requests.RequestException as e:
            print(f"[Godex] get_status network error for swap {swap_id}: {e}")
            return None
    
        if not response.ok:
            print(
                f"[Godex] get_status error {response.status_code} "
                f"for swap {swap_id}: {response.text}"
            )
            return None

    # Try JSON first (in case Godex fix their Content-Type), fall back to plain text
        try:
            data = response.json()
            godex_status = data.get("status", "").strip()
        except (json.JSONDecodeError, ValueError):
            godex_status = response.text.strip().strip('"')
    
        if not godex_status:
            print(f"[Godex] swap {swap_id} empty status response")
            return None
    
        print(f"[Godex] swap {swap_id} provider_status={godex_status}")
    
        if godex_status == "wait":
            return None
    
        elif godex_status in ("confirmation", "confirmed"):
            return "deposit"
    
        elif godex_status in ("exchanging", "sending", "sending_confirmation"):
            return "swapping"
    
        elif godex_status == "success":
            return "payout_confirmed"
    
        elif godex_status in ("overdue", "error", "refunded"):
            print(f"[Godex] swap {swap_id} terminal status: {godex_status}")
            return "failed"
    
        else:
            print(f"[Godex] swap {swap_id} unknown status: {godex_status}")
            return None
