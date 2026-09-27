#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri May  1 21:07:16 2026

@author: JustSwapping
"""

import sqlite3
import json
from datetime import datetime

SWAP_ID = 3  # clearly defined here

conn = sqlite3.connect("swaps.db")
cursor = conn.cursor()
now = datetime.utcnow().isoformat()

# Insert execution_started fact
cursor.execute("""
    INSERT INTO facts (swap_id, fact_type, source, confirmations, observed_at, last_updated)
    VALUES (?, ?, ?, ?, ?, ?)
""", (
    SWAP_ID, "execution_started",
    json.dumps({"provider": "mock", "provider_execution_id": "FAKE-PROVIDER-ID-3"}),
    1, now, now
))

# Insert provider_failed fact
cursor.execute("""
    INSERT INTO facts (swap_id, fact_type, source, confirmations, observed_at, last_updated)
    VALUES (?, ?, ?, ?, ?, ?)
""", (
    SWAP_ID, "provider_failed",
    json.dumps({"provider": "mock"}),
    1, now, now
))

conn.commit()
print(f"✅ facts inserted for swap #{SWAP_ID}")
conn.close()