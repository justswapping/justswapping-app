#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Apr  7 16:03:37 2026

@author: JustSwapping
"""

# models/swap.py

from dataclasses import dataclass
from typing import Optional


@dataclass
class Swap:
    """
    Canonical engine-owned representation of a swap.

    This object represents ENGINE TRUTH.
    Providers, routes, and UI must not mutate lifecycle state directly.
    """

    id: int

    # Swap intent
    from_coin: str
    to_coin: str
    amount: float

    # Engine-controlled state
    status: str
    provider: Optional[str] = None

# 02-05-26 add refund address
    # Addresses
    deposit_address: Optional[str] = None
    receive_address: Optional[str] = None
    refund_address:  Optional[str] = None

    # Metadata
    created_at: Optional[str] = None
    email: Optional[str] = None