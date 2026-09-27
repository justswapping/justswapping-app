#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat May  2 21:59:02 2026

@author: JustSwapping
"""

import sqlite3
import json
from datetime import datetime

SWAP_ID = 1

conn = sqlite3.connect("swaps.db")
cursor = conn.cursor()
cursor.execute("""
    INSERT INTO swaps (
        from_coin, to_coin, amount, receive_address, refund_address, deposit_address,
        status, email, provider, provider_execution_id,
        rate, withdrawal_amount, from_coin_gbp_rate, to_coin_gbp_rate,
        from_coin_usd_rate, to_coin_usd_rate
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
""", (
    "ltc", "xmr", 3.0,
    "8BbyGZ7WSZvZfNFjNZ8BDa5pF84dNAb25fcWbaGDcKfKPYjKM4ZcmZuepf2SUg9EC3VcTdrngVTHy1aR8bcFNfEmLDsBg2F",
    "ltc1qFAKEREFUNDADDRESS",
    "ltc1qFAKEDEPOSITADDRESS",
    "awaiting_deposit",
    "test@example.com",
    "mock", "FAKE-PROVIDER-ID",
    0.14, 0.43, 40.84, 276.16, 51.23, 346.50
))
conn.commit()
print("✅ fake swap inserted, id:", cursor.lastrowid)
conn.close()