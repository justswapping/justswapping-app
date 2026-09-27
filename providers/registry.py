#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Apr  7 16:27:41 2026

@author: JustSwapping
"""

# providers/registry.py

from typing import Dict
from providers.base import SwapProvider


class ProviderRegistry:
    """
    Central registry for all swap providers.

    The engine will ONLY interact with providers via this registry.
    """

    def __init__(self):
        self._providers: Dict[str, SwapProvider] = {}

    def register(self, provider: SwapProvider):
        self._providers[provider.name] = provider

    def get(self, name: str) -> SwapProvider:
        return self._providers[name]

    def all(self):
        return list(self._providers.values())