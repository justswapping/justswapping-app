#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat May  2 20:35:32 2026

@author: JustSwapping
"""

import sqlite3
import json
from datetime import datetime

# Simulate swap
# SWAP_ID = 1  # check what the next ID is first!

# conn = sqlite3.connect("swaps.db")
# cursor = conn.cursor()

# # Check current swaps first
# cursor.execute("SELECT id FROM swaps ORDER BY id DESC LIMIT 1")
# row = cursor.fetchone()
# print("Last swap ID:", row[0] if row else "none")
# conn.close()


# # Simulate execution_started fact
# SWAP_ID = 1

# conn = sqlite3.connect("swaps.db")
# cursor = conn.cursor()
# now = datetime.utcnow().isoformat()

# cursor.execute("""
#     INSERT INTO facts (swap_id, fact_type, source, confirmations, observed_at, last_updated)
#     VALUES (?, ?, ?, ?, ?, ?)
# """, (
#     SWAP_ID, "execution_started",
#     json.dumps({"provider": "mock", "provider_execution_id": "FAKE-PROVIDER-ID-1"}),
#     1, now, now
# ))

# conn.commit()
# print(f"✅ execution_started fact inserted for swap #{SWAP_ID}")
# conn.close()



import requests

SWAP_ID = 1

requests.post(f"http://127.0.0.1:5000/dev/simulate_deposit/{SWAP_ID}")
print("✅ deposit simulated")

requests.post(f"http://127.0.0.1:5000/engine/tick")
print("✅ tick 1")

requests.post(f"http://127.0.0.1:5000/dev/simulate_swapping/{SWAP_ID}")
print("✅ swapping simulated")

requests.post(f"http://127.0.0.1:5000/engine/tick")
print("✅ tick 2")

requests.post(f"http://127.0.0.1:5000/dev/simulate_payout_confirmed/{SWAP_ID}")
print("✅ payout confirmed simulated")

requests.post(f"http://127.0.0.1:5000/engine/tick")
print("✅ tick 3 — should be completed!")