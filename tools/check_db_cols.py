#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri May  1 16:02:22 2026

@author: JustSwapping
"""

import sqlite3
conn = sqlite3.connect("swaps.db")
conn.row_factory = sqlite3.Row
cursor = conn.cursor()
cursor.execute("SELECT id, from_coin, to_coin, amount, from_coin_gbp_rate, to_coin_gbp_rate, withdrawal_amount FROM swaps")
rows = cursor.fetchall()
for row in rows:
    print(dict(row))
conn.close()