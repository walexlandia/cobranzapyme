import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit import record_event
from app.database import get_db
from app.domain import ActorType, InvoiceStatus, Role
from app.models import Contact, Invoice, PayabilityItem, Payer
from app.routers.invoices import _authorized_client
from app.schemas import (
    ContactImportPreview,
    ImportIssue,
    ImportPreview,
    SiiStatusImportPreview,
)
from app.security import CurrentUser
from app.services.invoice_import import parse_contact_file, parse_invoice_file, parse_sii_status_file
from app.services.payability import ensure_checklist


router = APIRouter(prefix="/api/v1/imports", tags=["imports"])


@router.post("/invoices", response_model=ImportPreview)
async def import_invoices(
    user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    file: Annotated[UploadFile, File()],
    client_id: Annotated[uuid.UUID | None, Form()] = None,
    mapping: Annotated[str | None, Form()] = None,
    commit: Annotated[bool, Form()] = False,
) -> ImportPreview:
    scoped_client = _authorized_client(user, client_id)
    if user.role == Role.CLIENT and commit:
        raise HTTPException(status_code=403, detail="La importación definitiva requiere un operador")
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="El archivo supera 10 MB")
    try:
        rows, issues = parse_invoice_file(file.filename or "invoices.csv", content, mapping)
    except (UnicodeDecodeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    existing = set(
        db.execute(
            select(Invoice.document_type, Invoice.folio).where(Invoice.client_id == scoped_client)
        ).all()
    )
    accepted = []
    for row in rows:
        if (row.document_type, row.folio) in existing:
            issues.append(
                ImportIssue(row=row.row, field="folio", message="La factura ya existe para esta pyme")
            )
        else:
            accepted.append(row)

    imported_count = 0
    if commit and not issues:
        for row in accepted:
            payer = db.scalar(select(Payer).where(Payer.rut == row.payer_rut))
            if payer is None:
                payer = Payer(rut=row.payer_rut, legal_name=row.payer_name)
                db.add(payer)
                db.flush()
            invoice = Invoice(
                client_id=scoped_client,
                payer_id=payer.id,
                document_type=row.document_type,
                folio=row.folio,
                issued_on=row.issued_on,
                due_on=row.due_on,
                total_amount=row.total_amount,
                currency=row.currency,
                purchase_order=row.purchase_order,
                source="file_import",
            )
            db.add(invoice)
            db.flush()
            record_event(
                db,
                client_id=scoped_client,
                invoice_id=invoice.id,
                event_type="invoice.imported",
                actor_type=ActorType.HUMAN,
                actor_id=user.id,
                payload={"filename": file.filename, "source_row": row.row},
            )
            ensure_checklist(db, invoice, actor_type=ActorType.SYSTEM)
            imported_count += 1
        db.commit()

    return ImportPreview(
        valid_rows=accepted,
        issues=issues,
        can_commit=bool(accepted) and not issues,
        imported_count=imported_count,
    )


@router.post("/contacts", response_model=ContactImportPreview)
async def import_contacts(
    user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    file: Annotated[UploadFile, File()],
    client_id: Annotated[uuid.UUID | None, Form()] = None,
    mapping: Annotated[str | None, Form()] = None,
    commit: Annotated[bool, Form()] = False,
) -> ContactImportPreview:
    scoped_client = _authorized_client(user, client_id)
    if user.role == Role.CLIENT and commit:
        raise HTTPException(status_code=403, detail="La importación definitiva requiere un operador")
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="El archivo supera 10 MB")
    try:
        rows, issues = parse_contact_file(file.filename or "contacts.csv", content, mapping)
    except (UnicodeDecodeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    accepted = []
    for row in rows:
        payer = db.scalar(select(Payer).where(Payer.rut == row.payer_rut))
        if payer is None:
            accepted.append(row)
            continue
        duplicate = db.scalar(
            select(Contact.id).where(
                Contact.client_id == scoped_client,
                Contact.payer_id == payer.id,
                Contact.email == (str(row.email) if row.email else None),
                Contact.phone == row.phone,
            )
        )
        if duplicate:
            issues.append(ImportIssue(row=row.row, message="El contacto ya existe para esta pyme"))
        else:
            accepted.append(row)

    imported_count = 0
    if commit and not issues:
        for row in accepted:
            payer = db.scalar(select(Payer).where(Payer.rut == row.payer_rut))
            if payer is None:
                payer = Payer(rut=row.payer_rut, legal_name=row.payer_name)
                db.add(payer)
                db.flush()
            contact = Contact(
                client_id=scoped_client,
                payer_id=payer.id,
                name=row.name,
                role=row.role,
                email=str(row.email) if row.email else None,
                phone=row.phone,
            )
            db.add(contact)
            db.flush()
            record_event(
                db,
                client_id=scoped_client,
                event_type="contact.imported",
                actor_type=ActorType.HUMAN,
                actor_id=user.id,
                payload={"contact_id": str(contact.id), "payer_id": str(payer.id), "source_row": row.row},
            )
            imported_count += 1
        db.commit()

    return ContactImportPreview(
        valid_rows=accepted,
        issues=issues,
        can_commit=bool(accepted) and not issues,
        imported_count=imported_count,
    )


@router.post("/sii-status", response_model=SiiStatusImportPreview)
async def import_sii_status(
    user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
    file: Annotated[UploadFile, File()],
    client_id: Annotated[uuid.UUID | None, Form()] = None,
    mapping: Annotated[str | None, Form()] = None,
    commit: Annotated[bool, Form()] = False,
) -> SiiStatusImportPreview:
    scoped_client = _authorized_client(user, client_id)
    if user.role == Role.CLIENT and commit:
        raise HTTPException(status_code=403, detail="La importación definitiva requiere un operador")
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="El archivo supera 10 MB")
    try:
        rows, issues = parse_sii_status_file(file.filename or "sii-status.csv", content, mapping)
    except (UnicodeDecodeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    accepted: list[tuple] = []
    for row in rows:
        invoice = db.scalar(
            select(Invoice).where(
                Invoice.client_id == scoped_client,
                Invoice.document_type == row.document_type,
                Invoice.folio == row.folio,
            )
        )
        if invoice is None:
            issues.append(
                ImportIssue(
                    row=row.row,
                    field="folio",
                    message="La factura no existe para esta pyme",
                )
            )
        else:
            accepted.append((row, invoice))

    imported_count = 0
    if commit and not issues:
        for row, invoice in accepted:
            ensure_checklist(db, invoice, actor_type=ActorType.SYSTEM)
            item = db.scalar(
                select(PayabilityItem).where(
                    PayabilityItem.invoice_id == invoice.id,
                    PayabilityItem.item_type == "sii_acceptance",
                )
            )
            assert item is not None
            previous = {"status": item.status, "evidence": item.evidence}
            item.status = (
                "fulfilled"
                if row.sii_status == "accepted"
                else ("pending" if row.sii_status == "pending" else "blocked")
            )
            item.evidence = {
                "sii_status": row.sii_status,
                "checked_on": row.checked_on.isoformat(),
                "claim_deadline": row.claim_deadline.isoformat() if row.claim_deadline else None,
                "detail": row.detail,
                "source_file": file.filename,
                "source_row": row.row,
            }
            if row.sii_status in {"claimed", "rejected"}:
                invoice.status = InvoiceStatus.CLAIMED
            elif row.sii_status == "accepted" and invoice.status == InvoiceStatus.CLAIMED:
                invoice.status = InvoiceStatus.ISSUED
            record_event(
                db,
                client_id=scoped_client,
                invoice_id=invoice.id,
                event_type="payability.sii_status_imported",
                actor_type=ActorType.HUMAN,
                actor_id=user.id,
                payload={
                    "item_id": str(item.id),
                    "from": previous,
                    "to": {"status": item.status, "evidence": item.evidence},
                },
            )
            imported_count += 1
        db.commit()

    return SiiStatusImportPreview(
        valid_rows=[row for row, _ in accepted],
        issues=issues,
        can_commit=bool(accepted) and not issues,
        imported_count=imported_count,
    )

