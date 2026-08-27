"""Operator signing — the cryptographic identity boundary for T0 (H1).

T0 is the highest trust tier: operator authority, not a claim. It must NOT be
reachable from any text the model sees (a chat message, a file, a tool result).
Instead, a T0 write is bound to an Ed25519 signature made by the operator's
private key, which lives OFF the agent host (operator's device / keychain). The
host holds only the public key, so it can VERIFY a T0 write but can never FORGE
one — even a full host compromise cannot mint T0.

Signatures fail closed: if `cryptography` is not installed, or the public key is
missing, verification returns False and no T0 is written.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from milyonus.config.paths import data_root


def operator_pubkey_path() -> Path:
    return data_root() / "operator.pub"


def _load_backend():
    try:
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric.ed25519 import (
            Ed25519PrivateKey,
            Ed25519PublicKey,
        )

        return serialization, Ed25519PrivateKey, Ed25519PublicKey
    except ImportError:
        return None


def crypto_available() -> bool:
    return _load_backend() is not None


def generate_keypair(private_path: Path, public_path: Path | None = None) -> Path:
    """Create an operator keypair. The private key is the operator's secret;
    keep it OFF the agent host. Returns the public-key path (installed on host)."""
    backend = _load_backend()
    if backend is None:
        raise RuntimeError("cryptography not installed — run: pip install milyonus-agent[admin]")
    serialization, Ed25519PrivateKey, _ = backend
    priv = Ed25519PrivateKey.generate()
    private_path.write_bytes(
        priv.private_bytes(
            serialization.Encoding.PEM,
            serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption(),
        )
    )
    private_path.chmod(0o600)
    pub_path = public_path or operator_pubkey_path()
    pub_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    pub_path.write_bytes(
        priv.public_key().public_bytes(
            serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
        )
    )
    pub_path.chmod(0o644)
    return pub_path


def sign(private_path: Path, message: bytes) -> bytes:
    backend = _load_backend()
    if backend is None:
        raise RuntimeError("cryptography not installed — run: pip install milyonus-agent[admin]")
    serialization, _, _ = backend
    priv = serialization.load_pem_private_key(private_path.read_bytes(), password=None)
    return priv.sign(message)


def verify(message: bytes, signature: bytes, *, pubkey_path: Path | None = None) -> bool:
    """Verify a signature against the installed operator public key. Fail-closed."""
    backend = _load_backend()
    if backend is None:
        return False
    serialization, _, Ed25519PublicKey = backend
    path = pubkey_path or operator_pubkey_path()
    if not path.exists():
        return False
    try:
        pub = serialization.load_pem_public_key(path.read_bytes())
        if not isinstance(pub, Ed25519PublicKey):
            return False
        pub.verify(signature, message)
        return True
    except Exception:  # noqa: BLE001 - any failure is a verification failure
        return False


def fingerprint(pubkey_path: Path | None = None) -> str:
    path = pubkey_path or operator_pubkey_path()
    if not path.exists():
        return "(no operator key)"
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()[:16]
