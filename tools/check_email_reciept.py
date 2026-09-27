#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jul  8 13:32:57 2026

@author: JustSwapping
"""

from engine_helpers.email_receipt import send_completion_receipt
send_completion_receipt(
    swap_id=99,
    from_coin="ltc",
    to_coin="xmr",
    amount=2.0,
    withdrawal_amount=0.25679,
    receive_address="82xeiSD78wohpJQMWUM8D8a",
    provider="changenow",
    user_email="test@example.com",
    from_coin_gbp_rate=32.50,
    to_coin_gbp_rate=121.00,
    from_coin_usd_rate=43.44,
    to_coin_usd_rate=161.50,
)