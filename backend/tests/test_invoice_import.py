from app.services.invoice_import import parse_contact_file, parse_invoice_file


def test_parses_semicolon_csv_and_normalizes_values() -> None:
    content = (
        "RUT receptor;Razón social;Folio;Fecha emisión;Fecha vencimiento;Monto total;OC\n"
        "76.086.428-5;Pagador Demo;F-100;01-10-2026;31-10-2026;$1.250.000;OC-88\n"
    ).encode()

    rows, issues = parse_invoice_file("facturas.csv", content)

    assert issues == []
    assert len(rows) == 1
    assert rows[0].payer_rut == "76086428-5"
    assert rows[0].total_amount == 1250000
    assert rows[0].purchase_order == "OC-88"


def test_reports_duplicate_and_invalid_rows_before_commit() -> None:
    content = (
        "rut,payer_name,folio,issued_on,due_on,total_amount\n"
        "76.086.428-5,Pagador Demo,F-1,2026-10-01,2026-10-31,1000\n"
        "76.086.428-5,Pagador Demo,F-1,2026-10-01,2026-10-31,1000\n"
        "76.086.428-4,Pagador Demo,F-2,2026-10-01,2026-10-31,1000\n"
    ).encode()

    rows, issues = parse_invoice_file("facturas.csv", content)

    assert len(rows) == 1
    assert len(issues) == 2
    assert "duplicada" in issues[0].message
    assert "RUT inválido" in issues[1].message


def test_parses_contact_file_and_normalizes_role() -> None:
    content = (
        "RUT pagador;Razón social;Nombre contacto;Rol;Correo\n"
        "76.086.428-5;Pagador Demo;Ana Demo;Cuentas por pagar;ana@example.com\n"
    ).encode()

    rows, issues = parse_contact_file("contactos.csv", content)

    assert issues == []
    assert rows[0].role == "accounts_payable"
    assert str(rows[0].email) == "ana@example.com"

