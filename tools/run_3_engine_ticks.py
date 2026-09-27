#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Fri May  1 20:55:11 2026

@author: JustSwapping
"""

import requests

requests.post("http://127.0.0.1:5000/engine/tick")
print("✅ tick 1")
requests.post("http://127.0.0.1:5000/engine/tick")
print("✅ tick 2")
requests.post("http://127.0.0.1:5000/engine/tick")
print("✅ tick 3")