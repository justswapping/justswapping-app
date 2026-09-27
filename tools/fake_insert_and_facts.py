#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri May  1 21:18:06 2026

@author: JustSwapping
"""

import sqlite3
import json
from datetime import datetime

SWAP_ID = 7

conn = sqlite3.connect("swaps.db")
cursor = conn.cursor()
now = datetime.utcnow().isoformat()

# Insert fake swap
cursor.execute("""
    INSERT INTO swaps (
        from_coin, to_coin, amount, receive_address, deposit_address,
        status, email, provider, provider_execution_id,
        rate, withdrawal_amount, from_coin_gbp_rate, to_coin_gbp_rate
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
""", (
    "ltc", "xmr", 3.0,
    "8BbyGZ7WSZvZfNFjNZ8BDa5pF84dNAb25fcWbaGDcKfKPYjKM4ZcmZuepf2SUg9EC3VcTdrngVTHy1aR8bcFNfEmLDsBg2F",
    "ltc1qFAKEDEPOSITADDRESS",
    "awaiting_deposit",
    "test@example.com",
    "mock", "FAKE-PROVIDER-ID-4",
    0.14, 0.43, 40.84, 276.16
))

# Insert facts
for fact_type in ["execution_started", "provider_failed"]:
    cursor.execute("""
        INSERT INTO facts (swap_id, fact_type, source, confirmations, observed_at, last_updated)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (SWAP_ID, fact_type, json.dumps({"provider": "mock"}), 1, now, now))

conn.commit()
print(f"✅ swap #{SWAP_ID} and facts inserted")
conn.close()