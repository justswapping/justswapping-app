#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Deterministic mock provider used for Phase 8 development.
No external calls, no real swaps.
"""

from providers.base import SwapProvider

from engine_helpers.facts import _fact_type_exists


class MockProvider(SwapProvider):
    """
    Phase 8.4-compliant mock provider.

    Responsibilities:
    - Provide quotes
    - Create swaps (deposit details only)
    - Report execution facts via get_swap_status()

    Explicitly does NOT:
    - Control lifecycle
    - Write to the database
    - Return engine statuses
    """

    name = "mock"

    def get_quote(self, from_coin, to_coin, amount):
        # Simple deterministic conversion
        output_amount = amount * 0.95

        return {
            "provider": self.name,
            "output_amount": output_amount,
            "fee": 0.01,
            "meta": {
                "note": "simulated quote"
            }
        }

    # def create_swap(self, swap):
    #     """
    #     Create provider-backed execution details.
    #     Must NOT mutate lifecycle state.
    #     """
    #     return {
    #         "deposit_address": "mock_deposit_address_123",
    #         "expected_amount": swap.amount
    #     }
    
    def create_swap(self, swap):
        return {
            "deposit_address": "mock_deposit_address_123",
            "expected_amount": swap.amount,
            "provider_execution_id": f"mock-{id(swap)}"
        }

    # def get_status(self, swap):
    #     """
    #     Provider-level execution facts (NOT lifecycle states).

    #     Valid return values are interpreted by the engine.
    #     This function is read-only and deterministic.
    #     """

    #     swap_id = swap["id"]

    #     # Deterministic fake progression for Phase 8.4 testing
    #     if swap_id % 4 == 0:
    #         return "no_deposit"

    #     elif swap_id % 4 == 1:
    #         return "funds_seen"

    #     elif swap_id % 4 == 2:
    #         return "ready_to_swap"

    #     elif swap_id % 4 == 3:
    #         return "completed"
        
    # def get_status(self, swap):
    #     """
    #     Provider-level execution facts (NOT lifecycle states).
    
    #     Phase 2 mock behaviour:
    #     - None        -> nothing new to report
    #     - "swapping"  -> swap is in progress
    #     - "completed" -> swap has finished
    #     """
    
    #     swap_id = swap["id"]
    
    #     # Deterministic fake progression for Phase 2 testing
    #     if swap_id % 3 == 0:
    #         return None
    
    #     elif swap_id % 3 == 1:
    #         return "swapping"
    
    #     elif swap_id % 3 == 2:
    #         return "completed"
        
        
    # def get_status(self, swap):
        
    #     """
    #     Provider-level execution facts (NOT lifecycle states).
    
    #     DEV / deposit-flow testing behaviour:
    #     - No deposit fact -> provider reports nothing
    #     - Deposit present -> deterministic progression
    #     """
    
    #     swap_id = swap["id"]
    
    #     # ✅ NEW: do nothing until a deposit exists
    #     if not _fact_type_exists(swap_id, "deposit"):
    #         return None
    
    #     # ✅ AFTER deposit: deterministic fake progression
    #     if swap_id % 3 == 0:
    #         return None
    
    #     elif swap_id % 3 == 1:
    #         return "swapping"
    
    #     elif swap_id % 3 == 2:
    #         return "completed"
        
    def get_status(self, swap):
        swap_id = swap["id"]
        # breakpoint()
    
        if not _fact_type_exists(swap_id, "deposit"):
            return None
    
        if not _fact_type_exists(swap_id, "swapping"):
            return None
    
        if not _fact_type_exists(swap_id, "payout_confirmed"):
            return None

        return None