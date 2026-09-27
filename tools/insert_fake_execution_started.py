#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri May  1 20:52:19 2026

@author: JustSwapping
"""

import sqlite3
import json
from datetime import datetime

conn = sqlite3.connect("swaps.db")
cursor = conn.cursor()
now = datetime.utcnow().isoformat()

# Insert execution_started fact
cursor.execute("""
    INSERT INTO facts (swap_id, fact_type, source, confirmations, observed_at, last_updated)
    VALUES (?, ?, ?, ?, ?, ?)
""", (
    2, "execution_started",
    json.dumps({"provider": "mock", "provider_execution_id": "FAKE-PROVIDER-ID"}),
    1, now, now
))

# Reset status to awaiting_deposit so engine can advance it
cursor.execute("UPDATE swaps SET status = 'awaiting_deposit' WHERE id = 2")

conn.commit()
print("✅ done")
conn.close()