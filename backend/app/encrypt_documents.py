"""One-shot, idempotent encryption of legacy document contents."""

from sqlalchemy import or_, select

from app.database import SessionLocal
from app.document_crypto import encrypt_document_content
from app.models import Document


def main() -> None:
    with SessionLocal() as db:
        documents = list(
            db.scalars(
                select(Document).where(
                    Document.content.is_not(None),
                    or_(
                        Document.encryption_version.is_(None),
                        Document.encryption_version == "legacy_plaintext",
                    ),
                )
            )
        )
        for document in documents:
            content, nonce, version = encrypt_document_content(
                document_id=document.id,
                client_id=document.client_id,
                invoice_id=document.invoice_id,
                content=document.content or b"",
            )
            document.content = content
            document.encryption_nonce = nonce
            document.encryption_version = version
        db.commit()
        print(f"Encrypted {len(documents)} legacy documents")


if __name__ == "__main__":
    main()
