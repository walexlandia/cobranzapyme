import hashlib
import os
import uuid

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.models import Document


VERSION = "aesgcm-v1"


def _key() -> bytes:
    from app.config import settings

    return hashlib.sha256(settings.document_encryption_key.encode("utf-8")).digest()


def _aad(document_id: uuid.UUID, client_id: uuid.UUID, invoice_id: uuid.UUID | None) -> bytes:
    return f"recupera:{document_id}:{client_id}:{invoice_id or ''}".encode("utf-8")


def encrypt_document_content(
    *, document_id: uuid.UUID, client_id: uuid.UUID, invoice_id: uuid.UUID | None, content: bytes
) -> tuple[bytes, bytes, str]:
    nonce = os.urandom(12)
    ciphertext = AESGCM(_key()).encrypt(
        nonce, content, _aad(document_id, client_id, invoice_id)
    )
    return ciphertext, nonce, VERSION


def decrypt_document_content(document: Document) -> bytes | None:
    if document.content is None:
        return None
    if document.encryption_version in (None, "legacy_plaintext"):
        return document.content
    if document.encryption_version != VERSION or document.encryption_nonce is None:
        raise ValueError("Formato de cifrado documental no soportado")
    return AESGCM(_key()).decrypt(
        document.encryption_nonce,
        document.content,
        _aad(document.id, document.client_id, document.invoice_id),
    )
