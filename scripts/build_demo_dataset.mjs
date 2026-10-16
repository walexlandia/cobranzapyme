import fs from "node:fs/promises";
import path from "node:path";
import { SpreadsheetFile, Workbook } from "file:///C:/Users/alex.elias/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/@oai/artifact-tool/dist/artifact_tool.mjs";

const root = process.cwd();
const outputDir = path.join(root, "outputs");
const previewDir = path.join(outputDir, "previews-datos-prueba");
const demoDir = path.join(root, "data", "demo");
const csvDir = path.join(demoDir, "imports");
await fs.mkdir(outputDir, { recursive: true });
await fs.mkdir(previewDir, { recursive: true });
await fs.mkdir(csvDir, { recursive: true });

const asDate = (year, month, day) => new Date(Date.UTC(year, month - 1, day));
const addDays = (date, days) => new Date(date.getTime() + days * 86400000);
const isoDate = (date) => date ? date.toISOString().slice(0, 10) : "";
const asRut = (body) => {
  const digits = String(body);
  let sum = 0;
  let multiplier = 2;
  for (let index = digits.length - 1; index >= 0; index -= 1) {
    sum += Number(digits[index]) * multiplier;
    multiplier = multiplier === 7 ? 2 : multiplier + 1;
  }
  const result = 11 - (sum % 11);
  const verifier = result === 11 ? "0" : result === 10 ? "K" : String(result);
  return `${digits}-${verifier}`;
};

const currentDate = asDate(2026, 10, 14);

const pymes = [
  {
    id: "PYME-001",
    rut: asRut("76123456"),
    name: "Servicios Cordillera SpA",
    industry: "Mantenimiento industrial",
    city: "Antofagasta",
    baselineDso: 51.4,
    sender: "cobranzas.cordillera@example.com",
    payerIndexes: [0, 1, 2, 3, 4],
    slug: "cordillera",
  },
  {
    id: "PYME-002",
    rut: asRut("76543210"),
    name: "Ingeniería del Sur Ltda.",
    industry: "Ingeniería y proyectos",
    city: "Concepción",
    baselineDso: 46.2,
    sender: "finanzas.ingenieriadelsur@example.com",
    payerIndexes: [0, 2, 4, 5, 6],
    slug: "ingenieria-sur",
  },
  {
    id: "PYME-003",
    rut: asRut("77345678"),
    name: "Montajes Atacama SpA",
    industry: "Montaje eléctrico",
    city: "Copiapó",
    baselineDso: 57.8,
    sender: "administracion.montajesatacama@example.com",
    payerIndexes: [0, 1, 5, 6, 7],
    slug: "montajes-atacama",
  },
];

const payers = [
  { rut: asRut("96000111"), name: "Minera Horizonte S.A.", sector: "Minería", oc: true, hes: true, portal: true, dueDays: 45, paymentCycle: "Días 10 y 25" },
  { rut: asRut("96000222"), name: "Retail Pórtico S.A.", sector: "Retail", oc: true, hes: false, portal: true, dueDays: 30, paymentCycle: "Días 5 y 20" },
  { rut: asRut("96000333"), name: "Energía Austral SpA", sector: "Energía", oc: true, hes: true, portal: true, dueDays: 45, paymentCycle: "Viernes alternos" },
  { rut: asRut("96000444"), name: "Constructora Valle Central S.A.", sector: "Construcción", oc: true, hes: true, portal: false, dueDays: 30, paymentCycle: "Último día hábil" },
  { rut: asRut("96000555"), name: "Alimentos Pacífico Ltda.", sector: "Alimentos", oc: true, hes: false, portal: false, dueDays: 30, paymentCycle: "Días 15 y 30" },
  { rut: asRut("96000666"), name: "Celulosa Bosques del Sur S.A.", sector: "Forestal", oc: true, hes: true, portal: true, dueDays: 45, paymentCycle: "Día 28" },
  { rut: asRut("96000777"), name: "Logística Andina SpA", sector: "Logística", oc: false, hes: true, portal: true, dueDays: 30, paymentCycle: "Todos los jueves" },
  { rut: asRut("96000888"), name: "Clínica Metropolitana S.A.", sector: "Salud", oc: true, hes: false, portal: true, dueDays: 30, paymentCycle: "Días 12 y 27" },
];

const firstNames = ["Camila", "Tomás", "Valentina", "Diego", "Fernanda", "Matías", "Paula", "Sebastián"];
const lastNames = ["Rojas", "Muñoz", "Silva", "Contreras", "Sepúlveda", "Navarro", "Vega", "Paredes"];

const contacts = [];
for (let pymeIndex = 0; pymeIndex < pymes.length; pymeIndex += 1) {
  const pyme = pymes[pymeIndex];
  pyme.payerIndexes.forEach((payerIndex, relationIndex) => {
    const payer = payers[payerIndex];
    const sequence = pymeIndex * 5 + relationIndex;
    contacts.push({
      id: `CONT-${String(sequence + 1).padStart(3, "0")}`,
      pymeRut: pyme.rut,
      pyme: pyme.name,
      payerRut: payer.rut,
      payer: payer.name,
      name: `${firstNames[sequence % firstNames.length]} ${lastNames[(sequence + 2) % lastNames.length]}`,
      role: sequence % 3 === 0 ? "accounts_payable" : sequence % 3 === 1 ? "requester" : "other",
      email: `contacto${sequence + 1}@example.com`,
      phone: `+569${String(41000000 + sequence * 137).padStart(8, "0")}`,
      preferredChannel: sequence % 2 === 0 ? "email" : "whatsapp",
    });
  });
}

const invoices = [];
const payments = [];
const checklist = [];
const baseDate = asDate(2026, 6, 2);
let paymentSequence = 1;
let checklistSequence = 1;

for (let pymeIndex = 0; pymeIndex < pymes.length; pymeIndex += 1) {
  const pyme = pymes[pymeIndex];
  for (let index = 0; index < 40; index += 1) {
    const payer = payers[pyme.payerIndexes[index % pyme.payerIndexes.length]];
    const invoiceId = `FAC-${pymeIndex + 1}-${String(index + 1).padStart(4, "0")}`;
    const issueDate = addDays(baseDate, index * 3 + pymeIndex);
    const dueDate = addDays(issueDate, payer.dueDays);
    const scenario = (index + pymeIndex * 3) % 10;
    const amount = 380000 + ((index * 173000 + pymeIndex * 295000) % 5400000);
    let paidOn = null;
    let invoiceStatus = "emitida";
    let siiStatus = "aceptada";
    let delayCause = "";
    let notes = "";

    if (scenario === 0 || scenario === 8) {
      const candidate = addDays(dueDate, scenario === 0 ? -4 : -1);
      if (candidate <= currentDate) {
        paidOn = candidate;
        invoiceStatus = "pagada";
        notes = scenario === 8 ? "Problema documental resuelto antes del vencimiento" : "Pago normal";
      }
    } else if (scenario === 1 || scenario === 2 || scenario === 7) {
      const lateDays = scenario === 1 ? 12 : scenario === 2 ? 8 : 20;
      const candidate = addDays(dueDate, lateDays);
      delayCause = scenario === 1 ? "documental_hes_conformidad" : scenario === 2 ? "documental_portal" : "liquidez_pagador";
      if (candidate <= currentDate) {
        paidOn = candidate;
        invoiceStatus = "pagada";
        notes = scenario === 1 ? "HES emitida después del vencimiento" : scenario === 2 ? "Carga en portal completada tarde" : "Pagador informó restricción temporal de caja";
      } else {
        notes = "Caso abierto; fecha proyectada posterior a la fecha de corte";
      }
    } else if (scenario === 3) {
      delayCause = dueDate < currentDate ? "documental_oc" : "";
      notes = "OC pendiente del solicitante";
    } else if (scenario === 4) {
      notes = "Factura aprobada y programada para el próximo ciclo";
    } else if (scenario === 5) {
      siiStatus = "reclamada";
      invoiceStatus = "reclamada";
      delayCause = "documental_sii";
      notes = "Reclamo por referencia contractual incompleta";
    } else if (scenario === 6) {
      invoiceStatus = "disputa";
      delayCause = "disputa_comercial";
      notes = "Diferencia sobre alcance del servicio; requiere intervención humana";
    } else {
      notes = "Factura aún dentro de plazo";
    }

    if (!paidOn && dueDate < currentDate && !delayCause && invoiceStatus === "emitida") {
      delayCause = "proceso_interno_pagador";
    }

    const ocNumber = payer.oc && scenario !== 3 ? `OC-${pymeIndex + 1}${String(8100 + index).padStart(4, "0")}` : "";
    const hesMissingOpen = payer.hes && scenario === 1 && !paidOn;
    const hesNumber = payer.hes && !hesMissingOpen ? `HES-${pymeIndex + 1}${String(5200 + index).padStart(4, "0")}` : "";
    let portalDate = null;
    if (payer.portal && !(scenario === 2 && !paidOn)) {
      portalDate = scenario === 2 && paidOn ? addDays(dueDate, 6) : addDays(issueDate, 2);
    }
    const evidence = paidOn ? `evidencias/${invoiceId}-comprobante.pdf` : "";

    invoices.push({
      id: invoiceId,
      pymeRut: pyme.rut,
      pyme: pyme.name,
      payerRut: payer.rut,
      payer: payer.name,
      documentType: "factura",
      folio: `${pymeIndex + 1}${String(1000 + index).padStart(4, "0")}`,
      issueDate,
      dueDate,
      amount,
      currency: "CLP",
      ocRequired: payer.oc ? "Sí" : "No",
      ocNumber,
      hesRequired: payer.hes ? "Sí" : "No",
      hesNumber,
      portalRequired: payer.portal ? "Sí" : "No",
      portalDate,
      siiStatus,
      invoiceStatus,
      paidOn,
      delayCause,
      evidence,
      notes,
    });

    if (paidOn) {
      payments.push({
        id: `PAGO-${String(paymentSequence).padStart(4, "0")}`,
        invoiceId,
        pymeRut: pyme.rut,
        paidOn,
        amount,
        verified: paymentSequence % 7 === 0 ? "No" : "Sí",
        source: paymentSequence % 3 === 0 ? "cartola" : "comprobante",
        evidence,
      });
      paymentSequence += 1;
    }

    const checklistItems = [
      ["aceptacion_sii", siiStatus === "aceptada" ? "cumplido" : siiStatus === "reclamada" ? "reclamado" : "pendiente", "operador"],
      ["orden_compra", !payer.oc ? "no_aplica" : ocNumber ? "cumplido" : "pendiente", payer.oc ? "pagador" : "sistema"],
      ["hes_conformidad", !payer.hes ? "no_aplica" : hesNumber ? "cumplido" : "solicitado", payer.hes ? "pagador" : "sistema"],
      ["portal_proveedor", !payer.portal ? "no_aplica" : portalDate ? "cumplido" : "pendiente", payer.portal ? "operador" : "sistema"],
    ];
    checklistItems.forEach(([itemType, status, responsible]) => {
      checklist.push({
        id: `CHK-${String(checklistSequence).padStart(5, "0")}`,
        invoiceId,
        pymeRut: pyme.rut,
        itemType,
        status,
        responsible,
        updatedOn: paidOn || portalDate || issueDate,
        evidence: status === "cumplido" ? `evidencias/${invoiceId}-${itemType}.pdf` : "",
      });
      checklistSequence += 1;
    });
  }
}

const invalidRows = [
  ["76.086.428-4", "Pagador con RUT inválido", "factura", "ERR-001", asDate(2026, 10, 1), asDate(2026, 10, 31), 500000, "CLP", "", "RUT inválido"],
  [payers[0].rut, payers[0].name, "factura", "", asDate(2026, 10, 1), asDate(2026, 10, 31), 500000, "CLP", "OC-1", "Folio vacío"],
  [payers[0].rut, payers[0].name, "factura", "ERR-003", asDate(2026, 10, 20), asDate(2026, 10, 10), 500000, "CLP", "OC-2", "Vencimiento anterior a emisión"],
  [payers[1].rut, payers[1].name, "factura", "ERR-004", asDate(2026, 10, 1), asDate(2026, 10, 31), 0, "CLP", "OC-3", "Monto igual a cero"],
  [payers[1].rut, payers[1].name, "factura", "ERR-005", asDate(2026, 10, 1), asDate(2026, 10, 31), -100000, "CLP", "OC-4", "Monto negativo"],
  [payers[2].rut, payers[2].name, "factura", "DUP-001", asDate(2026, 10, 1), asDate(2026, 10, 31), 300000, "CLP", "OC-5", "Primera fila del duplicado"],
  [payers[2].rut, payers[2].name, "factura", "DUP-001", asDate(2026, 10, 2), asDate(2026, 11, 1), 300000, "CLP", "OC-6", "Folio duplicado"],
];

const workbook = Workbook.create();
const summary = workbook.worksheets.add("Resumen");
const invoicesSheet = workbook.worksheets.add("Facturas");
const contactsSheet = workbook.worksheets.add("Contactos");
const payersSheet = workbook.worksheets.add("Pagadores");
const pymesSheet = workbook.worksheets.add("Pymes");
const paymentsSheet = workbook.worksheets.add("Pagos");
const checklistSheet = workbook.worksheets.add("Checklist");
const invalidSheet = workbook.worksheets.add("Casos inválidos");
const guideSheet = workbook.worksheets.add("Guía");

const colors = {
  ink: "#17332D",
  green: "#176B52",
  greenLight: "#DDEDE6",
  sand: "#F4F0E7",
  amber: "#F7E7B3",
  red: "#F8D7D2",
  gray: "#6B756F",
  line: "#CFD8D3",
  white: "#FFFFFF",
};
const fontFamily = "Arial";

function styleSourceSheet(sheet, lastColumn, lastRow, tableName) {
  const used = sheet.getRange(`A1:${lastColumn}${lastRow}`);
  used.format.font = { name: fontFamily, size: 10, color: colors.ink };
  used.format.verticalAlignment = "center";
  const header = sheet.getRange(`A1:${lastColumn}1`);
  header.format = {
    fill: colors.green,
    font: { name: fontFamily, size: 10, bold: true, color: colors.white },
    horizontalAlignment: "center",
    verticalAlignment: "center",
    wrapText: true,
    borders: { preset: "inside", style: "thin", color: "#FFFFFF" },
  };
  header.format.rowHeight = 34;
  sheet.showGridLines = false;
  sheet.freezePanes.freezeRows(1);
  const table = sheet.tables.add(`A1:${lastColumn}${lastRow}`, true, tableName);
  table.style = "TableStyleMedium4";
  table.showBandedRows = true;
  table.showFilterButton = true;
}

// Pymes
pymesSheet.getRange("A1:H4").values = [
  ["Pyme ID", "RUT", "Razón social", "Rubro", "Ciudad", "DSO línea base", "Remitente", "Activa"],
  ...pymes.map((item) => [item.id, item.rut, item.name, item.industry, item.city, item.baselineDso, item.sender, "Sí"]),
];
styleSourceSheet(pymesSheet, "H", 4, "PymesTable");
pymesSheet.getRange("F2:F4").format.numberFormat = "0.0";
pymesSheet.getRange("A1:H4").format.autofitColumns();
pymesSheet.getRange("C2:C4").format.columnWidth = 30;
pymesSheet.getRange("G2:G4").format.columnWidth = 38;

// Pagadores
payersSheet.getRange(`A1:J${payers.length + 1}`).values = [
  ["RUT", "Razón social", "Sector", "Requiere OC", "Requiere HES", "Requiere portal", "Plazo pactado (días)", "Ciclo de pago", "Portal", "Datos ficticios"],
  ...payers.map((item, index) => [item.rut, item.name, item.sector, item.oc ? "Sí" : "No", item.hes ? "Sí" : "No", item.portal ? "Sí" : "No", item.dueDays, item.paymentCycle, item.portal ? `https://proveedores${index + 1}.example.test` : "", "Sí"]),
];
styleSourceSheet(payersSheet, "J", payers.length + 1, "PayersTable");
payersSheet.getRange(`A1:J${payers.length + 1}`).format.autofitColumns();
payersSheet.getRange(`B2:B${payers.length + 1}`).format.columnWidth = 34;
payersSheet.getRange(`I2:I${payers.length + 1}`).format.columnWidth = 36;

// Contactos
contactsSheet.getRange(`A1:J${contacts.length + 1}`).values = [
  ["Contacto ID", "RUT pyme", "Pyme", "RUT pagador", "Razón social", "Nombre contacto", "Rol", "Correo", "Teléfono", "Canal preferido"],
  ...contacts.map((item) => [item.id, item.pymeRut, item.pyme, item.payerRut, item.payer, item.name, item.role, item.email, item.phone, item.preferredChannel]),
];
styleSourceSheet(contactsSheet, "J", contacts.length + 1, "ContactsTable");
contactsSheet.getRange(`A1:J${contacts.length + 1}`).format.autofitColumns();
contactsSheet.getRange(`C2:C${contacts.length + 1}`).format.columnWidth = 30;
contactsSheet.getRange(`E2:E${contacts.length + 1}`).format.columnWidth = 34;
contactsSheet.getRange(`H2:H${contacts.length + 1}`).format.columnWidth = 32;

// Facturas
const invoiceRows = invoices.map((item) => [
  item.id, item.pymeRut, item.pyme, item.payerRut, item.payer, item.documentType,
  item.folio, item.issueDate, item.dueDate, item.amount, item.currency,
  item.ocRequired, item.ocNumber, item.hesRequired, item.hesNumber,
  item.portalRequired, item.portalDate, item.siiStatus, item.invoiceStatus,
  item.paidOn, item.delayCause, null, null, item.evidence, item.notes,
]);
invoicesSheet.getRange(`A1:Y${invoices.length + 1}`).values = [
  ["Factura ID", "RUT pyme", "Pyme", "RUT receptor", "Razón social", "Tipo documento", "Folio", "Fecha emisión", "Fecha vencimiento", "Monto total", "Moneda", "OC requerida", "OC", "HES requerida", "HES", "Portal requerido", "Fecha carga portal", "Estado SII", "Estado factura", "Fecha pago", "Causa atraso", "Días atraso", "Pagada en plazo", "Evidencia", "Notas"],
  ...invoiceRows,
];
invoicesSheet.getRange("V2").formulas = [["=IF(T2<>\"\",MAX(0,T2-I2),MAX(0,DATE(2026,10,14)-I2))"]];
invoicesSheet.getRange(`V2:V${invoices.length + 1}`).fillDown();
invoicesSheet.getRange("W2").formulas = [["=IF(T2=\"\",\"Pendiente\",IF(T2<=I2,\"Sí\",\"No\"))"]];
invoicesSheet.getRange(`W2:W${invoices.length + 1}`).fillDown();
styleSourceSheet(invoicesSheet, "Y", invoices.length + 1, "InvoicesTable");
invoicesSheet.freezePanes.freezeColumns(2);
invoicesSheet.getRange(`H2:I${invoices.length + 1}`).format.numberFormat = "yyyy-mm-dd";
invoicesSheet.getRange(`Q2:Q${invoices.length + 1}`).format.numberFormat = "yyyy-mm-dd";
invoicesSheet.getRange(`T2:T${invoices.length + 1}`).format.numberFormat = "yyyy-mm-dd";
invoicesSheet.getRange(`J2:J${invoices.length + 1}`).format.numberFormat = "$#,##0";
invoicesSheet.getRange(`V2:V${invoices.length + 1}`).format.numberFormat = "0";
invoicesSheet.getRange(`A1:Y${invoices.length + 1}`).format.autofitColumns();
for (const column of ["C", "E", "U", "X", "Y"]) invoicesSheet.getRange(`${column}2:${column}${invoices.length + 1}`).format.columnWidth = column === "Y" ? 48 : 30;
invoicesSheet.getRange(`S2:S${invoices.length + 1}`).conditionalFormats.add("containsText", { text: "reclamada", format: { fill: colors.red, font: { bold: true, color: "#9B2C22" } } });
invoicesSheet.getRange(`S2:S${invoices.length + 1}`).conditionalFormats.add("containsText", { text: "disputa", format: { fill: colors.amber, font: { bold: true, color: "#7A5711" } } });
invoicesSheet.getRange(`W2:W${invoices.length + 1}`).conditionalFormats.add("containsText", { text: "No", format: { fill: colors.red, font: { bold: true, color: "#9B2C22" } } });

// Pagos
paymentsSheet.getRange(`A1:H${payments.length + 1}`).values = [
  ["Pago ID", "Factura ID", "RUT pyme", "Fecha pago", "Monto", "Verificado", "Origen", "Evidencia"],
  ...payments.map((item) => [item.id, item.invoiceId, item.pymeRut, item.paidOn, item.amount, item.verified, item.source, item.evidence]),
];
styleSourceSheet(paymentsSheet, "H", payments.length + 1, "PaymentsTable");
paymentsSheet.getRange(`D2:D${payments.length + 1}`).format.numberFormat = "yyyy-mm-dd";
paymentsSheet.getRange(`E2:E${payments.length + 1}`).format.numberFormat = "$#,##0";
paymentsSheet.getRange(`A1:H${payments.length + 1}`).format.autofitColumns();
paymentsSheet.getRange(`H2:H${payments.length + 1}`).format.columnWidth = 38;

// Checklist
checklistSheet.getRange(`A1:H${checklist.length + 1}`).values = [
  ["Ítem ID", "Factura ID", "RUT pyme", "Tipo", "Estado", "Responsable", "Actualizado", "Evidencia"],
  ...checklist.map((item) => [item.id, item.invoiceId, item.pymeRut, item.itemType, item.status, item.responsible, item.updatedOn, item.evidence]),
];
styleSourceSheet(checklistSheet, "H", checklist.length + 1, "ChecklistTable");
checklistSheet.getRange(`G2:G${checklist.length + 1}`).format.numberFormat = "yyyy-mm-dd";
checklistSheet.getRange(`A1:H${checklist.length + 1}`).format.autofitColumns();
checklistSheet.getRange(`H2:H${checklist.length + 1}`).format.columnWidth = 42;
checklistSheet.getRange(`E2:E${checklist.length + 1}`).conditionalFormats.add("containsText", { text: "pendiente", format: { fill: colors.amber, font: { bold: true, color: "#7A5711" } } });
checklistSheet.getRange(`E2:E${checklist.length + 1}`).conditionalFormats.add("containsText", { text: "reclamado", format: { fill: colors.red, font: { bold: true, color: "#9B2C22" } } });

// Casos inválidos
invalidSheet.getRange(`A1:J${invalidRows.length + 1}`).values = [
  ["RUT receptor", "Razón social", "Tipo documento", "Folio", "Fecha emisión", "Fecha vencimiento", "Monto total", "Moneda", "OC", "Error esperado"],
  ...invalidRows,
];
styleSourceSheet(invalidSheet, "J", invalidRows.length + 1, "InvalidCasesTable");
invalidSheet.getRange(`E2:F${invalidRows.length + 1}`).format.numberFormat = "yyyy-mm-dd";
invalidSheet.getRange(`G2:G${invalidRows.length + 1}`).format.numberFormat = "$#,##0";
invalidSheet.getRange(`A2:J${invalidRows.length + 1}`).format.fill = colors.red;
invalidSheet.getRange(`A1:J${invalidRows.length + 1}`).format.autofitColumns();
invalidSheet.getRange(`B2:B${invalidRows.length + 1}`).format.columnWidth = 34;
invalidSheet.getRange(`J2:J${invalidRows.length + 1}`).format.columnWidth = 38;

// Resumen
summary.showGridLines = false;
summary.tabColor = colors.green;
summary.getRange("A2:H2").merge();
summary.getRange("A2").values = [["Datos de prueba de Recupera"]];
summary.getRange("A2").format.font = { name: fontFamily, size: 16, bold: true, color: colors.ink };
summary.getRange("A3:H3").format.borders = { bottom: { style: "thin", color: colors.green } };
summary.getRange("A4").values = [["Fecha de corte"]];
summary.getRange("B4").values = [[currentDate]];
summary.getRange("B4").format.numberFormat = "yyyy-mm-dd";
summary.getRange("A6:B6").values = [["Métrica", "Resultado"]];
summary.getRange("A7:A12").values = [["Facturas"], ["Monto facturado"], ["Facturas pagadas"], ["Pagadas en plazo"], ["Vencidas abiertas"], ["Atrasos documentales"]];
summary.getRange("B7:B12").formulas = [
  [`=COUNTA(Facturas!A2:A${invoices.length + 1})`],
  [`=SUM(Facturas!J2:J${invoices.length + 1})`],
  [`=COUNTIFS(Facturas!S2:S${invoices.length + 1},\"pagada\")`],
  [`=COUNTIFS(Facturas!W2:W${invoices.length + 1},\"Sí\")`],
  [`=COUNTIFS(Facturas!I2:I${invoices.length + 1},\"<\"&$B$4,Facturas!S2:S${invoices.length + 1},\"emitida\")`],
  [`=COUNTIFS(Facturas!U2:U${invoices.length + 1},\"documental_sii\")+COUNTIFS(Facturas!U2:U${invoices.length + 1},\"documental_oc\")+COUNTIFS(Facturas!U2:U${invoices.length + 1},\"documental_hes_conformidad\")+COUNTIFS(Facturas!U2:U${invoices.length + 1},\"documental_portal\")`],
];
summary.getRange("B8").format.numberFormat = "$#,##0";
summary.getRange("A6:B12").format.font = { name: fontFamily, size: 10, color: colors.ink };
summary.getRange("A6:B6").format = { fill: colors.green, font: { name: fontFamily, size: 10, bold: true, color: colors.white }, horizontalAlignment: "center", borders: { preset: "inside", style: "thin", color: colors.white } };
summary.getRange("A7:A12").format.fill = colors.greenLight;
summary.getRange("B7:B12").format.font = { name: fontFamily, size: 11, bold: true, color: colors.ink };
summary.getRange("A6:B12").format.borders = { preset: "outside", style: "thin", color: colors.line };

const causes = [
  "documental_sii",
  "documental_oc",
  "documental_hes_conformidad",
  "documental_portal",
  "liquidez_pagador",
  "disputa_comercial",
  "proceso_interno_pagador",
];
summary.getRange("A15:C15").values = [["Causa de atraso", "Facturas", "Monto"]];
summary.getRange(`A16:A${15 + causes.length}`).values = causes.map((cause) => [cause]);
for (let row = 16; row <= 15 + causes.length; row += 1) {
  summary.getRange(`B${row}`).formulas = [[`=COUNTIFS(Facturas!$U$2:$U$${invoices.length + 1},A${row})`]];
  summary.getRange(`C${row}`).formulas = [[`=SUMIFS(Facturas!$J$2:$J$${invoices.length + 1},Facturas!$U$2:$U$${invoices.length + 1},A${row})`]];
}
summary.getRange(`C16:C${15 + causes.length}`).format.numberFormat = "$#,##0";
summary.getRange("A15:C15").format = { fill: colors.green, font: { name: fontFamily, size: 10, bold: true, color: colors.white }, horizontalAlignment: "center", borders: { preset: "inside", style: "thin", color: colors.white } };
summary.getRange(`A16:A${15 + causes.length}`).format.fill = colors.greenLight;
summary.getRange(`A15:C${15 + causes.length}`).format.borders = { preset: "outside", style: "thin", color: colors.line };

summary.getRange("E6:H6").values = [["Pyme", "Facturas", "Monto", "% pagadas en plazo"]];
summary.getRange("E7:E9").values = pymes.map((item) => [item.name]);
for (let row = 7; row <= 9; row += 1) {
  summary.getRange(`F${row}`).formulas = [[`=COUNTIFS(Facturas!$C$2:$C$${invoices.length + 1},E${row})`]];
  summary.getRange(`G${row}`).formulas = [[`=SUMIFS(Facturas!$J$2:$J$${invoices.length + 1},Facturas!$C$2:$C$${invoices.length + 1},E${row})`]];
  summary.getRange(`H${row}`).formulas = [[`=COUNTIFS(Facturas!$C$2:$C$${invoices.length + 1},E${row},Facturas!$W$2:$W$${invoices.length + 1},\"Sí\")/COUNTIFS(Facturas!$C$2:$C$${invoices.length + 1},E${row},Facturas!$W$2:$W$${invoices.length + 1},\"<>Pendiente\")`]];
}
summary.getRange("G7:G9").format.numberFormat = "$#,##0";
summary.getRange("H7:H9").format.numberFormat = "0.0%";
summary.getRange("E6:H6").format = { fill: colors.green, font: { name: fontFamily, size: 10, bold: true, color: colors.white }, horizontalAlignment: "center", borders: { preset: "inside", style: "thin", color: colors.white } };
summary.getRange("E7:E9").format.fill = colors.greenLight;
summary.getRange("E6:H9").format.borders = { preset: "outside", style: "thin", color: colors.line };
summary.getRange("A25:H26").merge();
summary.getRange("A25").values = [["Todos los nombres, RUT, correos, teléfonos, portales, documentos y montos son ficticios. No representan empresas ni personas reales."]];
summary.getRange("A25").format = { fill: colors.amber, font: { name: fontFamily, size: 10, italic: true, color: colors.ink }, wrapText: true, verticalAlignment: "center" };
summary.getRange("A25:H26").format.rowHeight = 26;
summary.getRange("A1:A26").format.columnWidth = 31;
summary.getRange("B1:B26").format.columnWidth = 18;
summary.getRange("C1:C26").format.columnWidth = 18;
summary.getRange("D1:D26").format.columnWidth = 3;
summary.getRange("E1:E26").format.columnWidth = 31;
summary.getRange("F1:H26").format.columnWidth = 18;

// Guía
guideSheet.showGridLines = false;
guideSheet.tabColor = colors.gray;
guideSheet.getRange("A2:F2").merge();
guideSheet.getRange("A2").values = [["Guía de uso del dataset"]];
guideSheet.getRange("A2").format.font = { name: fontFamily, size: 16, bold: true, color: colors.ink };
guideSheet.getRange("A3:F3").format.borders = { bottom: { style: "thin", color: colors.green } };
const guideRows = [
  ["Contenido", "Descripción"],
  ["Resumen", "Indicadores calculados desde Facturas y Pagos con fecha de corte 2026-10-14."],
  ["Facturas", "120 facturas de tres pymes, con pagadores compartidos y distintos estados documentales y de pago."],
  ["Contactos", "Contactos por relación pyme-pagador. Se usa example.com, dominio reservado para documentación, para evitar envíos accidentales."],
  ["Pagadores", "Requisitos operativos ficticios: OC, HES, portal, plazo y ciclo de pago."],
  ["Pymes", "Tres clientes ficticios con línea base de DSO."],
  ["Pagos", "Pagos asociados a facturas. Algunos están sin verificar para probar la conciliación."],
  ["Checklist", "Cuatro ítems de pagabilidad por factura: SII, OC, HES y portal."],
  ["Casos inválidos", "Filas diseñadas para ser rechazadas por el importador."],
  ["Archivos CSV", "La carpeta data/demo/imports contiene facturas y contactos separados por pyme, más casos inválidos."],
  ["Privacidad", "Los datos son completamente sintéticos. No usar correos o teléfonos como si fueran contactos reales."],
];
guideSheet.getRange(`A5:B${4 + guideRows.length}`).values = guideRows;
guideSheet.getRange("A5:B5").format = { fill: colors.green, font: { name: fontFamily, size: 10, bold: true, color: colors.white }, horizontalAlignment: "center", borders: { preset: "inside", style: "thin", color: colors.white } };
guideSheet.getRange(`A6:A${4 + guideRows.length}`).format.fill = colors.greenLight;
guideSheet.getRange(`A6:B${4 + guideRows.length}`).format.font = { name: fontFamily, size: 10, color: colors.ink };
guideSheet.getRange(`A5:B${4 + guideRows.length}`).format.borders = { preset: "outside", style: "thin", color: colors.line };
guideSheet.getRange(`B6:B${4 + guideRows.length}`).format.wrapText = true;
guideSheet.getRange(`A6:B${4 + guideRows.length}`).format.verticalAlignment = "top";
guideSheet.getRange(`A1:A${4 + guideRows.length}`).format.columnWidth = 24;
guideSheet.getRange(`B1:B${4 + guideRows.length}`).format.columnWidth = 86;
guideSheet.getRange(`A5:B${4 + guideRows.length}`).format.autofitRows();

invoicesSheet.tabColor = "#31856C";
contactsSheet.tabColor = "#62A88E";
payersSheet.tabColor = "#62A88E";
pymesSheet.tabColor = "#62A88E";
paymentsSheet.tabColor = "#7AAE9D";
checklistSheet.tabColor = "#7AAE9D";
invalidSheet.tabColor = "#B95548";

workbook.recalculate();

const summaryInspect = await workbook.inspect({
  kind: "table",
  range: "Resumen!A2:H26",
  include: "values,formulas",
  tableMaxRows: 26,
  tableMaxCols: 8,
  maxChars: 12000,
});
console.log(summaryInspect.ndjson);

const formulaErrors = await workbook.inspect({
  kind: "match",
  searchTerm: "#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!",
  options: { useRegex: true, maxResults: 300 },
  summary: "final formula error scan",
});
console.log(formulaErrors.ndjson);

for (const sheetName of ["Resumen", "Facturas", "Contactos", "Pagadores", "Pymes", "Pagos", "Checklist", "Casos inválidos", "Guía"]) {
  const preview = await workbook.render({ sheetName, autoCrop: "all", scale: sheetName === "Resumen" ? 1.3 : 0.8, format: "png" });
  await fs.writeFile(path.join(previewDir, `${sheetName.replaceAll(" ", "-").toLowerCase()}.png`), new Uint8Array(await preview.arrayBuffer()));
}

const output = await SpreadsheetFile.exportXlsx(workbook);
const workbookPath = path.join(outputDir, "recupera-datos-prueba.xlsx");
await output.save(workbookPath);

function csvEscape(value) {
  if (value === null || value === undefined) return "";
  const normalized = value instanceof Date ? isoDate(value) : String(value);
  return normalized.includes(";") || normalized.includes("\"") || normalized.includes("\n")
    ? `"${normalized.replaceAll("\"", "\"\"")}"`
    : normalized;
}

async function writeCsv(filename, headers, rows) {
  const content = [headers, ...rows].map((row) => row.map(csvEscape).join(";")).join("\n") + "\n";
  await fs.writeFile(path.join(csvDir, filename), content, "utf8");
}

for (const pyme of pymes) {
  const pymeInvoices = invoices.filter((item) => item.pymeRut === pyme.rut);
  await writeCsv(
    `facturas-${pyme.slug}.csv`,
    ["RUT receptor", "Razón social", "Tipo documento", "Folio", "Fecha emisión", "Fecha vencimiento", "Monto total", "Moneda", "OC"],
    pymeInvoices.map((item) => [item.payerRut, item.payer, item.documentType, item.folio, item.issueDate, item.dueDate, item.amount, item.currency, item.ocNumber]),
  );
  const pymeContacts = contacts.filter((item) => item.pymeRut === pyme.rut);
  await writeCsv(
    `contactos-${pyme.slug}.csv`,
    ["RUT pagador", "Razón social", "Nombre contacto", "Rol", "Correo", "Teléfono"],
    pymeContacts.map((item) => [item.payerRut, item.payer, item.name, item.role === "accounts_payable" ? "Cuentas por pagar" : item.role === "requester" ? "Solicitante" : "Otro", item.email, item.phone]),
  );
  await writeCsv(
    `estado-sii-${pyme.slug}.csv`,
    ["Tipo documento", "Folio", "Estado SII", "Fecha consulta", "Plazo reclamo", "Detalle"],
    pymeInvoices.map((item) => [
      item.documentType,
      item.folio,
      item.siiStatus === "aceptada" ? "Aceptada" : "Reclamada",
      addDays(item.issueDate, 8),
      addDays(item.issueDate, 8),
      item.siiStatus === "reclamada" ? "Caso sintético con referencia contractual incompleta" : "",
    ]),
  );
}

const payerProfiles = payers.map((payer, index) => ({
  rut: payer.rut,
  legal_name: payer.name,
  requires_purchase_order: payer.oc,
  requires_hes: payer.hes,
  requires_delivery_note: index % 3 === 1,
  requires_supplier_portal: payer.portal,
  risk_days_before_due: 5 + (index % 3) * 5,
  payment_cycle: payer.paymentCycle,
  portal: payer.portal ? `https://proveedores${index + 1}.example.test` : null,
  supplier_portal_instructions: payer.portal
    ? "Ingresar factura y respaldos requeridos; conservar el número de ingreso."
    : null,
}));
await fs.writeFile(
  path.join(demoDir, "payer-profiles.json"),
  JSON.stringify(payerProfiles, null, 2) + "\n",
  "utf8",
);

await writeCsv(
  "facturas-invalidas.csv",
  ["RUT receptor", "Razón social", "Tipo documento", "Folio", "Fecha emisión", "Fecha vencimiento", "Monto total", "Moneda", "OC"],
  invalidRows.map((row) => row.slice(0, 9)),
);

const manifest = {
  generatedAt: "2026-10-14",
  synthetic: true,
  pymes: pymes.length,
  payers: payers.length,
  contacts: contacts.length,
  invoices: invoices.length,
  payments: payments.length,
  checklistItems: checklist.length,
  siiStatusRows: invoices.length,
  payerProfiles: payerProfiles.length,
  invalidRows: invalidRows.length,
};
await fs.writeFile(path.join(csvDir, "manifest.json"), JSON.stringify(manifest, null, 2) + "\n", "utf8");
console.log(JSON.stringify({ workbookPath, previewDir, csvDir, manifest }, null, 2));

