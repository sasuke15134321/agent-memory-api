#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AES-256-GCM encryption engine for agent memory
Key is loaded from ENCRYPTION_KEY environment variable
"""

import os
import base64
import hashlib
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


class EncryptionEngine:
    def __init__(self):
        key_str = os.getenv("ENCRYPTION_KEY", "")
        if not key_str:
            print("[WARN] ENCRYPTION_KEY not set — encryption disabled (plaintext storage)")
            self._enabled = False
            self._aesgcm = None
        else:
            # Derive 32-byte key via SHA-256 so any string length works
            self._key = hashlib.sha256(key_str.encode()).digest()
            self._aesgcm = AESGCM(self._key)
            self._enabled = True
            print("[OK] AES-256-GCM encryption engine initialized")

    @property
    def enabled(self) -> bool:
        return self._enabled

    def encrypt(self, plaintext: str) -> str:
        """Encrypt plaintext string; returns base64(nonce[12] + ciphertext+tag)"""
        if not self._enabled:
            return plaintext
        nonce = os.urandom(12)
        ciphertext = self._aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
        return base64.b64encode(nonce + ciphertext).decode("ascii")

    def decrypt(self, data: str) -> str:
        """Decrypt base64-encoded ciphertext back to plaintext"""
        if not self._enabled:
            return data
        try:
            raw = base64.b64decode(data.encode("ascii"))
            nonce = raw[:12]
            ciphertext = raw[12:]
            plaintext = self._aesgcm.decrypt(nonce, ciphertext, None)
            return plaintext.decode("utf-8")
        except Exception as e:
            print(f"[WARN] Decryption failed, returning raw value: {e}")
            return data


# Global singleton
encryption_engine = EncryptionEngine()
