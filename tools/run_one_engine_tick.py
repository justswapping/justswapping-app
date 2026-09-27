#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri May  1 21:08:39 2026

@author: JustSwapping
"""

import requests
requests.post("http://127.0.0.1:5000/engine/tick")
print("✅ tick done")