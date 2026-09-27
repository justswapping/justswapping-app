#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Apr  7 15:56:05 2026

@author: JustSwapping
"""

# providers/base.py

class SwapProvider:
    """
    Abstract swap provider interface.
    Engine code must ONLY interact with providers via this interface.
    """

    name = "abstract"

    def get_quote(self, from_coin, to_coin, amount):
        """
        Return a dict:
        {
            "provider": str,
            "output_amount": float,
            "fee": float,
            "meta": dict
        }
        """
        raise NotImplementedError

    def create_swap(self, swap):
        """
        Create a swap with the external provider.

        Returns provider-specific metadata, but MUST NOT
        mutate swap state directly.
        """
        raise NotImplementedError

    def get_status(self, swap):
        """
        Return provider-facing status (string or enum).
        """
        raise NotImplementedError