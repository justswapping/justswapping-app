#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Check the status of a swap directly with a provider.

Usage:
    python tools/godex_status_check.py godex <transaction_id>
    python tools/godex_status_check.py changenow <exchange_id>

The ChangeNOW check reads CHANGENOW_API_KEY from your .env file.
"""
import os
import sys

import requests
from dotenv import load_dotenv

load_dotenv()

if len(sys.argv) != 3 or sys.argv[1] not in ("godex", "changenow"):
    print(__doc__)
    sys.exit(1)

provider, swap_id = sys.argv[1], sys.argv[2]

if provider == "godex":
    url = f"https://api.godex.io/api/v1/transaction/{swap_id}/status"
    response = requests.get(url, timeout=15)
else:
    api_key = os.environ.get("CHANGENOW_API_KEY")
    if not api_key:
        sys.exit("CHANGENOW_API_KEY is not set in your .env file")
    response = requests.get(
        "https://api.changenow.io/v2/exchange/by-id",
        params={"id": swap_id},
        headers={"x-changenow-api-key": api_key},
        timeout=15,
    )

print("Status code:", response.status_code)
print("Response:", response.text)