#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri May  1 20:48:30 2026

@author: JustSwapping
"""

# import sqlite3
# conn = sqlite3.connect("swaps.db")
# cursor = conn.cursor()
# cursor.execute("""
#     INSERT INTO swaps (
#         from_coin, to_coin, amount, receive_address, deposit_address,
#         status, email, provider, provider_execution_id,
#         rate, withdrawal_amount, from_coin_gbp_rate, to_coin_gbp_rate
#     ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
# """, (
#     "ltc", "xmr", 3.0,
#     "8BbyGZ7WSZvZfNFjNZ8BDa5pF84dNAb25fcWbaGDcKfKPYjKM4ZcmZuepf2SUg9EC3VcTdrngVTHy1aR8bcFNfEmLDsBg2F",
#     "ltc1qFAKEDEPOSITADDRESS",
#     "awaiting_deposit",
#     "test@example.com",
#     "mock", "FAKE-PROVIDER-ID",
#     0.14, 0.43, 40.84, 276.16
# ))
# conn.commit()
# print("✅ fake swap inserted, id:", cursor.lastrowid)
# conn.close()

# 02-05-26 refund address added

import sqlite3

# SWAP_ID_LABEL = "fake swap"

import sqlite3
conn = sqlite3.connect("swaps.db")
cursor = conn.cursor()

cursor.execute("""
    INSERT INTO swaps (
        from_coin, to_coin, amount, receive_address, refund_address, deposit_address,
        status, email, provider, provider_execution_id,
        rate, withdrawal_amount, from_coin_gbp_rate, to_coin_gbp_rate
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
""", (
    "ltc", "xmr", 3.0,
    "8BbyGZ7WSZvZfNFjNZ8BDa5pF84dNAb25fcWbaGDcKfKPYjKM4ZcmZuepf2SUg9EC3VcTdrngVTHy1aR8bcFNfEmLDsBg2F",
    "ltc1qFAKEREFUNDADDRESS",
    "ltc1qFAKEDEPOSITADDRESS",
    "awaiting_deposit",
    "test@example.com",
    "mock", "FAKE-PROVIDER-ID",
    0.14, 0.43, 40.84, 276.16
))

conn.commit()
print("✅ fake swap inserted, id:", cursor.lastrowid)
conn.close()