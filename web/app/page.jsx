"use client";

import { useCallback, useEffect, useMemo, useState } from "react";

const statusLabels = {
  issued: "Emitida",
  paid: "Pagada",
  void: "Anulada",
  claimed: "Reclamada",
  disputed: "En disputa",
};

const stageLabels = {
  emission: "Emisión",
  documental: "Validación documental",
  preventive: "Preventiva",
  due: "Vencimiento",
  early_arrears: "Mora temprana",
  escalation: "Escalamiento",
  closed: "Cerrada",
};

const eventLabels = {
  "invoice.status_changed": "Estado de factura actualizado",
  "workflow.state_changed": "Estado del flujo recalculado",
  "workflow.job_scheduled": "Acción programada",
  "workflow.action_ready": "Acción lista para ejecutar",
  "workflow.paused": "Gestión pausada",
  "workflow.resumed": "Gestión reanudada",
  "payability.item_created": "Requisito de pagabilidad creado",
  "payability.item_changed": "Requisito de pagabilidad actualizado",
  "payability.requirement_changed": "Regla del pagador actualizada",
  "payability.sii_status_imported": "Estado SII importado",
  "payability.portal_registered": "Carga en portal registrada",
  "payability.preventive_confirmation_changed": "Confirmación preventiva actualizada",
  "delay_cause.changed": "Causa de atraso registrada",
  "communication.template_version_created": "Versión de plantilla creada",
  "communication.draft_created": "Borrador de comunicación creado",
  "communication.blocked": "Comunicación bloqueada",
  "communication.opt_out_changed": "Preferencia de contacto actualizada",
  "communication.simulated": "Entrega simulada",
  "communication.received": "Respuesta recibida",
  "communication.manual_response_recorded": "Respuesta manual registrada",
  "communication.delivery_status_changed": "Estado de entrega actualizado",
  "classification.created": "Clasificación supervisada creada",
  "classification.human_decision": "Decisión humana registrada",
  "classification.checklist_correction_applied": "Checklist corregido por una persona",
  "classification.workflow_stage_corrected": "Etapa corregida por una persona",
  "classification.policy_changed": "Política de clasificación actualizada",
  "evaluation.example_added": "Ejemplo anonimizado agregado",
  "evaluation.set_frozen": "Set de evaluación congelado",
  "exception.escalated_to_client": "Excepción escalada localmente",
  "exception.response_draft_created": "Respuesta asistida preparada",
  "payer_profile.proposal_created": "Mejora de ficha propuesta",
  "payer_profile.proposal_decided": "Mejora de ficha revisada",
  "bank_transaction.imported": "Movimiento bancario importado",
  "reconciliation.proposed": "Conciliación propuesta",
  "reconciliation.confirmed": "Conciliación confirmada",
  "reconciliation.rejected": "Conciliación rechazada",
  "payment.verified": "Pago verificado",
  "payment.attribution_calculated": "Atribución contractual calculada",
  "pilot.authorization_recorded": "Autorización del piloto registrada",
  "pilot.authorization_revoked": "Autorización del piloto revocada",
  "client_document.submitted": "Documento enviado por la pyme",
  "client_document.reviewed": "Documento de la pyme revisado",
};

const payabilityLabels = {
  payable: "Pagable",
  incomplete: "Incompleta",
  at_risk: "En riesgo",
  claimed: "Reclamada",
};

const itemStatusLabels = {
  pending: "Pendiente",
  requested: "Solicitado",
  fulfilled: "Cumplido",
  not_applicable: "No aplica",
  blocked: "Bloqueado",
};

const money = new Intl.NumberFormat("es-CL", {
  style: "currency",
  currency: "CLP",
  maximumFractionDigits: 0,
});

function ApiStatus({ state }) {
  const labels = { checking: "Verificando API", ready: "Sistema disponible", offline: "API sin conexión" };
  return <div className={`system-status ${state}`}><i /> {labels[state]}</div>;
}

function Message({ value, onClose }) {
  if (!value) return null;
  return (
    <div className={`message ${value.type ?? "info"}`} role="status">
      <span>{value.text}</span>
      <button type="button" onClick={onClose} aria-label="Cerrar mensaje">×</button>
    </div>
  );
}

function Login({ apiUrl, apiState, onAuthenticated }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const body = new URLSearchParams({ username: email, password });
      const response = await fetch(`${apiUrl}/api/v1/auth/token`, {
        method: "POST",
        headers: { "Content-Type": "application/x-www-form-urlencoded" },
        body,
      });
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail ?? "No fue posible iniciar sesión");
      onAuthenticated(payload.access_token);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="login-shell">
      <section className="login-story">
        <div className="brand brand-light"><span>R</span> Recupera</div>
        <div>
          <p className="eyebrow light">OPERACIÓN DE CUENTAS POR COBRAR</p>
          <h1>Facturas pagables.<br /><em>Seguimiento verificable.</em></h1>
          <p>Una consola para importar, validar y gestionar facturas sin perder el aislamiento entre pymes.</p>
        </div>
        <p className="login-foot">Fase 7 · Piloto asistido y producto demostrable</p>
      </section>
      <section className="login-panel">
        <div className="login-card">
          <ApiStatus state={apiState} />
          <p className="kicker">ACCESO SEGURO</p>
          <h2>Entrar a la operación</h2>
          <p className="muted">Usa las credenciales configuradas en el entorno local.</p>
          <form onSubmit={submit}>
            <label>Correo<input type="email" value={email} onChange={(event) => setEmail(event.target.value)} required /></label>
            <label>Contraseña<input type="password" value={password} onChange={(event) => setPassword(event.target.value)} required /></label>
            {error && <p className="field-error">{error}</p>}
            <button className="primary full" disabled={busy || apiState === "offline"}>{busy ? "Ingresando…" : "Iniciar sesión"}</button>
          </form>
          <p className="security-note">La sesión se conserva solo en esta pestaña del navegador.</p>
        </div>
      </section>
    </main>
  );
}

function Stat({ label, value, note }) {
  return <article className="stat-card"><span>{label}</span><strong>{value}</strong><small>{note}</small></article>;
}

function ImportPanel({ kind, clientId, request, onImported }) {
  const isInvoice = kind === "invoices";
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function send(commit) {
    if (!file || !clientId) return;
    setBusy(true);
    setError("");
    const form = new FormData();
    form.append("file", file);
    form.append("client_id", clientId);
    form.append("commit", String(commit));
    try {
      const result = await request(`/api/v1/imports/${kind}`, { method: "POST", body: form });
      setPreview(result);
      if (commit && result.imported_count > 0) onImported(result.imported_count);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
    }
  }

  function selectFile(event) {
    setFile(event.target.files?.[0] ?? null);
    setPreview(null);
    setError("");
  }

  return (
    <article className="import-card">
      <div className="card-heading">
        <div><p className="kicker">{isInvoice ? "E3-01 / E3-02" : "E3-03"}</p><h3>{isInvoice ? "Importar facturas" : "Importar contactos"}</h3></div>
        <span className="file-type">CSV · XLSX</span>
      </div>
      <p className="muted">{isInvoice ? "Valida RUT, fechas, montos y duplicados antes de guardar." : "Asocia contactos y roles al pagador correspondiente."}</p>
      <label className="dropzone">
        <input type="file" accept=".csv,.xlsx" onChange={selectFile} />
        <b>{file ? file.name : "Seleccionar archivo"}</b>
        <span>{file ? `${Math.ceil(file.size / 1024)} KB` : "Máximo 10 MB"}</span>
      </label>
      {error && <p className="field-error">{error}</p>}
      <div className="button-row">
        <button type="button" className="secondary" disabled={!file || busy} onClick={() => send(false)}>{busy ? "Validando…" : "Validar archivo"}</button>
        <button type="button" className="primary" disabled={!preview?.can_commit || busy} onClick={() => send(true)}>Confirmar importación</button>
      </div>
      {preview && (
        <div className={`preview ${preview.issues.length ? "has-errors" : "valid"}`}>
          <div className="preview-summary"><b>{preview.valid_rows.length} filas válidas</b><span>{preview.issues.length ? `${preview.issues.length} observaciones` : "Sin observaciones"}</span></div>
          {preview.imported_count > 0 && <p className="success-line">Se importaron {preview.imported_count} registros.</p>}
          {preview.issues.length > 0 && <ul>{preview.issues.slice(0, 6).map((issue, index) => <li key={`${issue.row}-${index}`}>Fila {issue.row}: {issue.message}</li>)}</ul>}
          {!preview.issues.length && preview.valid_rows.length > 0 && (
            <div className="sample-rows">{preview.valid_rows.slice(0, 3).map((row) => <span key={row.row}>{isInvoice ? `${row.folio} · ${row.payer_name}` : `${row.name} · ${row.payer_name}`}</span>)}</div>
          )}
        </div>
      )}
    </article>
  );
}

function SiiImportPanel({ clientId, request, onImported }) {
  const [file, setFile] = useState(null);
  const [preview, setPreview] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function send(commit) {
    if (!file || !clientId) return;
    setBusy(true);
    setError("");
    const form = new FormData();
    form.append("file", file);
    form.append("client_id", clientId);
    form.append("commit", String(commit));
    try {
      const result = await request("/api/v1/imports/sii-status", { method: "POST", body: form });
      setPreview(result);
      if (commit && result.imported_count > 0) onImported(result.imported_count);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
    }
  }

  return <article className="import-card">
    <div className="card-heading"><div><p className="kicker">EP-04</p><h3>Importar estado SII</h3></div><span className="file-type">CSV · XLSX</span></div>
    <p className="muted">Actualiza aceptación, reclamo y plazo legal usando un archivo exportado o preparado por el operador.</p>
    <label className="dropzone"><input type="file" accept=".csv,.xlsx" onChange={(event) => { setFile(event.target.files?.[0] ?? null); setPreview(null); }} /><b>{file ? file.name : "Seleccionar archivo SII"}</b><span>Folio, estado y fecha de consulta</span></label>
    {error && <p className="field-error">{error}</p>}
    <div className="button-row"><button type="button" className="secondary" disabled={!file || busy} onClick={() => send(false)}>Validar archivo</button><button type="button" className="primary" disabled={!preview?.can_commit || busy} onClick={() => send(true)}>Aplicar estados</button></div>
    {preview && <div className={`preview ${preview.issues.length ? "has-errors" : "valid"}`}><div className="preview-summary"><b>{preview.valid_rows.length} facturas encontradas</b><span>{preview.issues.length ? `${preview.issues.length} observaciones` : "Sin observaciones"}</span></div>{preview.imported_count > 0 && <p className="success-line">Se actualizaron {preview.imported_count} facturas.</p>}{preview.issues.length > 0 && <ul>{preview.issues.slice(0, 6).map((issue, index) => <li key={`${issue.row}-${index}`}>Fila {issue.row}: {issue.message}</li>)}</ul>}</div>}
  </article>;
}

function ClientForm({ request, onCreated, onCancel }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [form, setForm] = useState({ name: "", rut: "", sender_name: "", sender_email: "", baseline_dso: "" });
  const change = (event) => setForm((current) => ({ ...current, [event.target.name]: event.target.value }));

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const created = await request("/api/v1/clients", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          ...form,
          sender_name: form.sender_name || null,
          sender_email: form.sender_email || null,
          baseline_dso: form.baseline_dso ? Number(form.baseline_dso) : null,
          bank_details: {},
        }),
      });
      onCreated(created);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="modal-backdrop" role="presentation">
      <section className="modal" role="dialog" aria-modal="true" aria-labelledby="client-title">
        <div className="card-heading"><div><p className="kicker">E1-04</p><h2 id="client-title">Crear cliente</h2></div><button type="button" className="icon-button" onClick={onCancel} aria-label="Cerrar">×</button></div>
        <form onSubmit={submit} className="client-form">
          <label>Razón social<input name="name" value={form.name} onChange={change} required minLength={2} /></label>
          <label>RUT<input name="rut" value={form.rut} onChange={change} placeholder="76.123.456-0" required /></label>
          <label>Nombre remitente<input name="sender_name" value={form.sender_name} onChange={change} /></label>
          <label>Correo remitente<input name="sender_email" type="email" value={form.sender_email} onChange={change} /></label>
          <label>DSO línea base<input name="baseline_dso" type="number" min="0" step="0.1" value={form.baseline_dso} onChange={change} /></label>
          {error && <p className="field-error wide">{error}</p>}
          <div className="button-row wide end"><button type="button" className="ghost" onClick={onCancel}>Cancelar</button><button className="primary" disabled={busy}>{busy ? "Creando…" : "Crear cliente"}</button></div>
        </form>
      </section>
    </div>
  );
}

function PauseDialog({ target, onCancel, onConfirm }) {
  const [reason, setReason] = useState("promise_of_payment");
  const [resumeAt, setResumeAt] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    try {
      await onConfirm(reason, resumeAt);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="modal-backdrop" role="presentation">
      <section className="modal compact-modal" role="dialog" aria-modal="true" aria-labelledby="pause-title">
        <div className="card-heading"><div><p className="kicker">CONTROL OPERATIVO</p><h2 id="pause-title">Pausar {target.label}</h2></div><button type="button" className="icon-button" onClick={onCancel} aria-label="Cerrar">×</button></div>
        <form className="pause-form" onSubmit={submit}>
          <label>Motivo<select value={reason} onChange={(event) => setReason(event.target.value)}><option value="promise_of_payment">Promesa de pago</option><option value="operator_review">Revisión del operador</option><option value="missing_document">Documento pendiente</option><option value="payer_request">Solicitud del pagador</option></select></label>
          <label>Reanudar automáticamente (opcional)<input type="datetime-local" value={resumeAt} onChange={(event) => setResumeAt(event.target.value)} /></label>
          <p className="form-hint">Si no defines fecha, la pausa permanecerá activa hasta que un operador la reanude.</p>
          <div className="button-row end"><button type="button" className="ghost" onClick={onCancel}>Cancelar</button><button className="primary" disabled={busy}>{busy ? "Guardando…" : "Confirmar pausa"}</button></div>
        </form>
      </section>
    </div>
  );
}

function EventTimeline({ invoice, events, loading, onClose }) {
  return (
    <div className="modal-backdrop" role="presentation">
      <section className="modal timeline-modal" role="dialog" aria-modal="true" aria-labelledby="timeline-title">
        <div className="card-heading"><div><p className="kicker">TRAZABILIDAD INMUTABLE</p><h2 id="timeline-title">Factura {invoice.folio}</h2><p className="muted">{invoice.payer_name}</p></div><button type="button" className="icon-button" onClick={onClose} aria-label="Cerrar">×</button></div>
        <div className="timeline-list">
          {events.map((event) => (
            <article key={event.id} className="timeline-item">
              <time>{new Date(event.created_at).toLocaleString("es-CL")}</time>
              <div><b>{eventLabels[event.event_type] ?? event.event_type}</b><span>{event.actor_type} · {event.mode}</span><pre>{JSON.stringify(event.payload, null, 2)}</pre></div>
            </article>
          ))}
          {!loading && !events.length && <p className="empty-version">Esta factura todavía no tiene eventos registrados.</p>}
          {loading && <p className="empty-version">Cargando historial…</p>}
        </div>
      </section>
    </div>
  );
}

function PayabilityDialog({ checklist, canOperate, clientId, request, onClose, onChanged }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [portal, setPortal] = useState({ entry_number: "", uploaded_at: new Date().toISOString().slice(0, 16), evidence_reference: "" });
  const [preventive, setPreventive] = useState({ approval_status: "approved", scheduled_payment_date: "", reference: "" });
  const [delay, setDelay] = useState({ category: "purchase_order", detail: "" });

  async function updateItem(item, status) {
    setBusy(true); setError("");
    try {
      await request(`/api/v1/payability/items/${item.id}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ status, evidence: { ...item.evidence, updated_from_console: true } }) });
      await onChanged();
    } catch (requestError) { setError(requestError.message); } finally { setBusy(false); }
  }

  async function registerPortal(event) {
    event.preventDefault(); setBusy(true); setError("");
    try {
      await request(`/api/v1/payability/invoices/${checklist.invoice_id}/portal?client_id=${clientId}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ ...portal, uploaded_at: new Date(portal.uploaded_at).toISOString() }) });
      await onChanged();
    } catch (requestError) { setError(requestError.message); } finally { setBusy(false); }
  }

  async function saveDelay(event) {
    event.preventDefault(); setBusy(true); setError("");
    try {
      await request(`/api/v1/payability/invoices/${checklist.invoice_id}/delay-cause?client_id=${clientId}`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(delay) });
    } catch (requestError) { setError(requestError.message); } finally { setBusy(false); }
  }

  async function savePreventive(event) {
    event.preventDefault(); setBusy(true); setError("");
    try {
      await request(`/api/v1/payability/invoices/${checklist.invoice_id}/preventive-confirmation?client_id=${clientId}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ approval_status: preventive.approval_status, approved_at: new Date().toISOString(), scheduled_payment_date: preventive.approval_status === "approved" && preventive.scheduled_payment_date ? preventive.scheduled_payment_date : null, reference: preventive.reference || null }) });
      await onChanged();
    } catch (requestError) { setError(requestError.message); } finally { setBusy(false); }
  }

  const portalItem = checklist.items.find((item) => item.item_type === "supplier_portal" && item.required);
  const preventiveItems = checklist.items.some((item) => item.item_type === "payment_approval");
  return <div className="modal-backdrop" role="presentation"><section className="modal payability-modal" role="dialog" aria-modal="true" aria-labelledby="payability-title">
    <div className="card-heading"><div><p className="kicker">EP-03 / EP-07</p><h2 id="payability-title">Pagabilidad · {checklist.folio}</h2><p className="muted">{checklist.payer_name}</p></div><div className="modal-title-actions"><span className={`payability-pill ${checklist.status}`}>{payabilityLabels[checklist.status]}</span><button type="button" className="icon-button" onClick={onClose} aria-label="Cerrar">×</button></div></div>
    <div className="payability-body">
      <div className="checklist-summary"><b>{checklist.completed} de {checklist.total} requisitos cumplidos</b><span>{checklist.missing_items.length ? `Faltan: ${checklist.missing_items.join(", ")}` : "Sin requisitos bloqueantes pendientes"}</span></div>
      {error && <p className="field-error">{error}</p>}
      <div className="checklist-list">{checklist.items.map((item) => { const isPreventive = ["payment_approval", "payment_scheduled"].includes(item.item_type); return <article key={item.id}><div><b>{item.label}</b><span>{item.required ? "Obligatorio" : "Seguimiento preventivo"} · Responsable: {item.responsible_role}</span></div>{canOperate && !isPreventive ? <select disabled={busy} value={item.status} onChange={(event) => updateItem(item, event.target.value)}>{Object.entries(itemStatusLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select> : <span className={`item-status ${item.status}`}>{itemStatusLabels[item.status]}</span>}</article>; })}</div>
      {canOperate && portalItem && <form className="embedded-form" onSubmit={registerPortal}><h4>Evidencia de portal</h4><div className="form-grid"><label>Número de ingreso<input required value={portal.entry_number} onChange={(event) => setPortal((current) => ({ ...current, entry_number: event.target.value }))} /></label><label>Fecha de carga<input type="datetime-local" required value={portal.uploaded_at} onChange={(event) => setPortal((current) => ({ ...current, uploaded_at: event.target.value }))} /></label><label className="wide">Referencia de evidencia<input required placeholder="Archivo, captura o ruta de custodia" value={portal.evidence_reference} onChange={(event) => setPortal((current) => ({ ...current, evidence_reference: event.target.value }))} /></label></div><button className="secondary" disabled={busy}>Registrar carga</button></form>}
      {canOperate && preventiveItems && <form className="embedded-form" onSubmit={savePreventive}><h4>Aprobación y programación preventiva</h4><div className="form-grid"><label>Decisión<select value={preventive.approval_status} onChange={(event) => setPreventive((current) => ({ ...current, approval_status: event.target.value, scheduled_payment_date: event.target.value === "rejected" ? "" : current.scheduled_payment_date }))}><option value="approved">Aprobada para pago</option><option value="rejected">Rechazada</option></select></label><label>Fecha programada<input type="date" required={preventive.approval_status === "approved"} disabled={preventive.approval_status === "rejected"} value={preventive.scheduled_payment_date} onChange={(event) => setPreventive((current) => ({ ...current, scheduled_payment_date: event.target.value }))} /></label><label className="wide">Referencia<input placeholder="Correo, ticket o confirmación de CxP" value={preventive.reference} onChange={(event) => setPreventive((current) => ({ ...current, reference: event.target.value }))} /></label></div><button className="secondary" disabled={busy}>Registrar confirmación</button></form>}
      {canOperate && <form className="embedded-form" onSubmit={saveDelay}><h4>Causa de atraso</h4><div className="form-grid"><label>Categoría<select value={delay.category} onChange={(event) => setDelay((current) => ({ ...current, category: event.target.value }))}><option value="sii_acceptance">Aceptación SII</option><option value="purchase_order">Orden de compra</option><option value="hes_conformity">HES / conformidad</option><option value="supplier_portal">Portal de proveedores</option><option value="payment_data">Datos de pago</option><option value="payer_liquidity">Liquidez del pagador</option><option value="commercial_dispute">Disputa comercial</option><option value="other">Otra</option></select></label><label>Detalle<input value={delay.detail} onChange={(event) => setDelay((current) => ({ ...current, detail: event.target.value }))} /></label></div><button className="secondary" disabled={busy}>Guardar causa</button></form>}
    </div>
  </section></div>;
}

function PayabilityPanel({ clientId, selectedClient, request, onClientUpdated }) {
  const [payers, setPayers] = useState([]);
  const [payerId, setPayerId] = useState("");
  const [profile, setProfile] = useState(null);
  const [summary, setSummary] = useState([]);
  const [message, setMessage] = useState(null);
  const [busy, setBusy] = useState(false);
  const [form, setForm] = useState({ requires_purchase_order: true, requires_hes: false, requires_delivery_note: false, requires_supplier_portal: false, risk_days_before_due: 7, supplier_portal_url: "", supplier_portal_instructions: "", payment_cycle: "", corporate_email: "", corporate_phone: "", other_requirements_text: "" });
  const [baseline, setBaseline] = useState({ baseline_dso: "", baseline_on_time_percent: "", baseline_late_distribution: "{}" });

  useEffect(() => {
    if (!clientId) return;
    Promise.all([request(`/api/v1/payers?client_id=${clientId}`), request(`/api/v1/payability/delay-causes?client_id=${clientId}`)]).then(([rows, causes]) => { setPayers(rows); setSummary(causes); setPayerId((current) => rows.some((item) => item.id === current) ? current : rows[0]?.id ?? ""); }).catch((error) => setMessage({ type: "error", text: error.message }));
  }, [clientId, request]);

  useEffect(() => {
    if (!payerId) { setProfile(null); return; }
    request(`/api/v1/payers/${payerId}/profile?client_id=${clientId}`).then((value) => { setProfile(value); const rules = value.operational_requirements; setForm({ requires_purchase_order: rules.requires_purchase_order, requires_hes: rules.requires_hes, requires_delivery_note: rules.requires_delivery_note, requires_supplier_portal: rules.requires_supplier_portal, risk_days_before_due: rules.risk_days_before_due, supplier_portal_url: value.supplier_portal_url ?? "", supplier_portal_instructions: value.supplier_portal_instructions ?? "", payment_cycle: value.payment_cycle ?? "", corporate_email: value.corporate_channels?.email ?? "", corporate_phone: value.corporate_channels?.phone ?? "", other_requirements_text: (rules.other_requirements ?? []).map((item) => `${item.code}|${item.label}|${item.responsible_role}`).join("\n") }); }).catch((error) => setMessage({ type: "error", text: error.message }));
  }, [payerId, clientId, request]);

  useEffect(() => { if (selectedClient) setBaseline({ baseline_dso: selectedClient.baseline_dso ?? "", baseline_on_time_percent: selectedClient.baseline_on_time_percent ?? "", baseline_late_distribution: JSON.stringify(selectedClient.baseline_late_distribution ?? {}, null, 2) }); }, [selectedClient]);
  const change = (event) => setForm((current) => ({ ...current, [event.target.name]: event.target.type === "checkbox" ? event.target.checked : event.target.value }));

  async function saveProfile(event) {
    event.preventDefault(); setBusy(true); setMessage(null);
    try {
      const otherRequirements = form.other_requirements_text.split("\n").map((line) => line.trim()).filter(Boolean).map((line) => { const [code, label, responsible_role = "client"] = line.split("|").map((part) => part.trim()); return { code, label, responsible_role }; });
      const updated = await request(`/api/v1/payers/${payerId}/profile`, { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ operational_requirements: { requires_purchase_order: form.requires_purchase_order, requires_hes: form.requires_hes, requires_delivery_note: form.requires_delivery_note, requires_supplier_portal: form.requires_supplier_portal, other_requirements: otherRequirements, risk_days_before_due: Number(form.risk_days_before_due) }, supplier_portal_url: form.supplier_portal_url || null, supplier_portal_instructions: form.supplier_portal_instructions || null, payment_cycle: form.payment_cycle || null, corporate_channels: { ...(form.corporate_email ? { email: form.corporate_email } : {}), ...(form.corporate_phone ? { phone: form.corporate_phone } : {}) } }) });
      setProfile(updated); setMessage({ type: "success", text: `Ficha global guardada como versión ${updated.version}.` });
    } catch (error) { setMessage({ type: "error", text: error.message }); } finally { setBusy(false); }
  }

  async function saveBaseline(event) {
    event.preventDefault(); setBusy(true); setMessage(null);
    try {
      const updated = await request(`/api/v1/clients/${clientId}/baseline`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ baseline_dso: baseline.baseline_dso === "" ? null : Number(baseline.baseline_dso), baseline_on_time_percent: baseline.baseline_on_time_percent === "" ? null : Number(baseline.baseline_on_time_percent), baseline_late_distribution: JSON.parse(baseline.baseline_late_distribution || "{}") }) });
      onClientUpdated(updated); setMessage({ type: "success", text: "Línea base guardada." });
    } catch (error) { setMessage({ type: "error", text: error.message }); } finally { setBusy(false); }
  }

  return <section className="payability-layout"><article className="contract-card"><div className="card-heading"><div><p className="kicker">EP-01 / EP-02</p><h3>Ficha global del pagador</h3></div><select value={payerId} onChange={(event) => setPayerId(event.target.value)}>{payers.map((payer) => <option key={payer.id} value={payer.id}>{payer.legal_name}</option>)}</select></div>{profile && <form className="contract-form" onSubmit={saveProfile}><div className="form-section"><h4>Requisitos para pagar</h4><div className="check-row"><label><input type="checkbox" name="requires_purchase_order" checked={form.requires_purchase_order} onChange={change} /> Orden de compra</label><label><input type="checkbox" name="requires_hes" checked={form.requires_hes} onChange={change} /> HES / conformidad</label><label><input type="checkbox" name="requires_delivery_note" checked={form.requires_delivery_note} onChange={change} /> Guía de despacho</label><label><input type="checkbox" name="requires_supplier_portal" checked={form.requires_supplier_portal} onChange={change} /> Portal de proveedores</label></div><label className="other-requirements">Requisitos adicionales<textarea rows="4" name="other_requirements_text" value={form.other_requirements_text} onChange={change} placeholder="codigo|Descripción|client&#10;certificado|Certificado vigente|requester" /><span>Una línea por requisito: código|descripción|responsable.</span></label></div><div className="form-section"><div className="form-grid"><label>Días para marcar riesgo<input type="number" min="1" max="30" name="risk_days_before_due" value={form.risk_days_before_due} onChange={change} /></label><label>Ciclo de pago<input name="payment_cycle" value={form.payment_cycle} onChange={change} /></label><label>Correo corporativo CxP<input type="email" name="corporate_email" value={form.corporate_email} onChange={change} /></label><label>Teléfono corporativo<input name="corporate_phone" value={form.corporate_phone} onChange={change} /></label><label className="wide">URL portal<input name="supplier_portal_url" value={form.supplier_portal_url} onChange={change} /></label><label className="wide">Instrucciones del portal<textarea rows="4" name="supplier_portal_instructions" value={form.supplier_portal_instructions} onChange={change} /></label></div></div><div className="button-row end"><span className="read-only">Versión global {profile.version}</span><button className="primary" disabled={busy}>Guardar nueva versión</button></div></form>}</article><aside className="profile-side"><article className="version-card"><p className="kicker">LÍNEA BASE</p><h3>{selectedClient?.name}</h3><form className="baseline-form" onSubmit={saveBaseline}><label>DSO histórico<input type="number" min="0" step="0.1" value={baseline.baseline_dso} onChange={(event) => setBaseline((current) => ({ ...current, baseline_dso: event.target.value }))} /></label><label>Pagado a tiempo (%)<input type="number" min="0" max="100" step="0.1" value={baseline.baseline_on_time_percent} onChange={(event) => setBaseline((current) => ({ ...current, baseline_on_time_percent: event.target.value }))} /></label><label>Distribución histórica (JSON)<textarea rows="5" value={baseline.baseline_late_distribution} onChange={(event) => setBaseline((current) => ({ ...current, baseline_late_distribution: event.target.value }))} /></label><button className="secondary" disabled={busy}>Guardar línea base</button></form></article><article className="version-card"><p className="kicker">E11-06</p><h3>Causas de atraso</h3><div className="cause-list">{summary.map((item) => <div key={item.category}><b>{item.category}</b><span>{item.invoice_count} facturas</span><small>{money.format(Number(item.total_amount))}</small></div>)}{!summary.length && <p className="empty-version">Aún no hay causas registradas.</p>}</div></article><Message value={message} onClose={() => setMessage(null)} /></aside></section>;
}

function CommunicationsPanel({ clientId, request }) {
  const [messages, setMessages] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [contacts, setContacts] = useState([]);
  const [invoices, setInvoices] = useState([]);
  const [jobs, setJobs] = useState([]);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState(null);
  const [form, setForm] = useState({ template_key: "payment_due", channel: "email", stage: "due", recipient_role: "accounts_payable", tone: "cordial", subject_template: "Seguimiento de facturas · {client_name} · {payer_name}", body_template: "Hola {recipient_name}:\n\nEscribimos en representación de {client_name} respecto de {invoice_summary}.\n\n{action_request}{missing_items_section}{bank_details_section}\n\nSaludos,\n{sender_name}", approved: false });
  const [inboundForm, setInboundForm] = useState({ channel: "email", provider_id: "demo-inbound-001", sender: "", external_thread_key: "", in_reply_to_provider_id: "", subject: "RE: Estado de factura", body: "Confirmamos recepción. La factura quedó programada para el próximo ciclo de pagos.", invoice_folios: "", attachment_names: "acuse-recepcion.pdf" });
  const [manualForm, setManualForm] = useState({ contact_id: "", invoice_id: "", channel: "phone", subject: "Respuesta recibida por teléfono", body: "El contacto informa que revisará el estado y confirmará la fecha de pago." });

  const load = useCallback(async () => {
    if (!clientId) return;
    try {
      const [messageRows, templateRows, contactRows, jobRows, invoiceRows] = await Promise.all([
        request(`/api/v1/communications/messages?client_id=${clientId}`),
        request(`/api/v1/communications/templates?client_id=${clientId}`),
        request(`/api/v1/communications/contacts?client_id=${clientId}`),
        request(`/api/v1/workflows/jobs?client_id=${clientId}&limit=30`),
        request(`/api/v1/invoices?client_id=${clientId}`),
      ]);
      setMessages(messageRows); setTemplates(templateRows); setContacts(contactRows); setJobs(jobRows); setInvoices(invoiceRows);
      setInboundForm((current) => ({ ...current, sender: current.sender || contactRows.find((contact) => contact.email)?.email || "", invoice_folios: current.invoice_folios || invoiceRows[0]?.folio || "" }));
      setManualForm((current) => ({ ...current, invoice_id: current.invoice_id || invoiceRows[0]?.id || "", contact_id: current.contact_id || contactRows.find((contact) => contact.payer_id === invoiceRows[0]?.payer_id)?.id || "" }));
    } catch (error) { setNotice({ type: "error", text: error.message }); }
  }, [clientId, request]);

  useEffect(() => { load(); }, [load]);

  async function prepare(job) {
    setBusy(true); setNotice(null);
    try {
      const message = await request(`/api/v1/communications/jobs/${job.id}/prepare?client_id=${clientId}`, { method: "POST" });
      setNotice({ type: message.status === "blocked" ? "error" : "success", text: message.status === "blocked" ? `Borrador bloqueado: ${message.safety_flags.join(", ")}.` : "Borrador preparado sin envío externo." });
      await load();
    } catch (error) { setNotice({ type: "error", text: error.message }); } finally { setBusy(false); }
  }

  async function simulate(message) {
    setBusy(true); setNotice(null);
    try {
      await request(`/api/v1/communications/messages/${message.id}/simulate?client_id=${clientId}`, { method: "POST" });
      setNotice({ type: "success", text: "Entrega simulada localmente; no se contactó a ningún destinatario." });
      await load();
    } catch (error) { setNotice({ type: "error", text: error.message }); } finally { setBusy(false); }
  }

  async function updateDelivery(message, status) {
    setBusy(true); setNotice(null);
    try {
      await request(`/api/v1/communications/messages/${message.id}/delivery-status`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ client_id: clientId, status, detail: "Estado actualizado desde simulador local" }) });
      setNotice({ type: status === "failed" ? "error" : "success", text: `Estado local actualizado a ${status}; no hubo interacción externa.` });
      await load();
    } catch (error) { setNotice({ type: "error", text: error.message }); } finally { setBusy(false); }
  }

  async function recordInbound(event) {
    event.preventDefault(); setBusy(true); setNotice(null);
    try {
      const created = await request("/api/v1/communications/inbound/simulate", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ client_id: clientId, channel: inboundForm.channel, provider_id: inboundForm.provider_id, sender: inboundForm.sender, external_thread_key: inboundForm.external_thread_key || null, in_reply_to_provider_id: inboundForm.in_reply_to_provider_id || null, subject: inboundForm.channel === "email" ? inboundForm.subject || null : null, body: inboundForm.body, invoice_folios: inboundForm.invoice_folios.split(",").map((value) => value.trim()).filter(Boolean), attachments: inboundForm.attachment_names.split("\n").map((value) => value.trim()).filter(Boolean).map((original_name) => ({ original_name, kind: "reply_attachment" })) }) });
      setNotice({ type: "success", text: `Entrada ${created.channel} correlacionada con ${created.invoice_folios.length} factura(s).` });
      setInboundForm((current) => ({ ...current, provider_id: `demo-inbound-${Date.now()}` }));
      await load();
    } catch (error) { setNotice({ type: "error", text: error.message }); } finally { setBusy(false); }
  }

  async function recordManual(event) {
    event.preventDefault(); setBusy(true); setNotice(null);
    try {
      const created = await request("/api/v1/communications/manual-responses", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ client_id: clientId, contact_id: manualForm.contact_id || null, invoice_ids: [manualForm.invoice_id], channel: manualForm.channel, subject: manualForm.subject || null, body: manualForm.body }) });
      setNotice({ type: "success", text: `Respuesta manual registrada para ${created.invoice_folios.join(", ")}.` });
      await load();
    } catch (error) { setNotice({ type: "error", text: error.message }); } finally { setBusy(false); }
  }

  async function saveTemplate(event) {
    event.preventDefault(); setBusy(true); setNotice(null);
    try {
      const created = await request("/api/v1/communications/templates", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ ...form, client_id: clientId, subject_template: form.channel === "email" ? form.subject_template : null }) });
      setNotice({ type: "success", text: `Plantilla ${created.template_key} guardada como versión ${created.version}.` });
      await load();
    } catch (error) { setNotice({ type: "error", text: error.message }); } finally { setBusy(false); }
  }

  async function optOut(contact, channel, optedOut) {
    setBusy(true); setNotice(null);
    try {
      await request(`/api/v1/communications/contacts/${contact.id}/opt-out`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ client_id: clientId, channel, opted_out: optedOut, reason: "Actualización desde consola local" }) });
      setNotice({ type: "success", text: `${channel === "email" ? "Email" : "WhatsApp"} ${optedOut ? "bloqueado" : "habilitado"} para ${contact.name}.` });
      await load();
    } catch (error) { setNotice({ type: "error", text: error.message }); } finally { setBusy(false); }
  }

  const preparedJobIds = new Set(messages.map((message) => message.workflow_job_id).filter(Boolean));
  const selectedManualInvoice = invoices.find((invoice) => invoice.id === manualForm.invoice_id);
  const eligibleManualContacts = contacts.filter((contact) => !selectedManualInvoice || contact.payer_id === selectedManualInvoice.payer_id);
  return <section className="communications-layout">
    <Message value={notice} onClose={() => setNotice(null)} />
    <article className="outbox-card"><div className="card-heading"><div><p className="kicker">E5-01 A E5-05 / E5-10</p><h3>Bandeja bidireccional simulada</h3></div><button type="button" className="ghost" onClick={load}>Actualizar</button></div><div className="message-list">{messages.map((message) => <article key={message.id} className={`communication-item ${message.status} ${message.direction}`}><header><div><span className="channel-pill">{message.direction === "inbound" ? "ENTRADA" : "SALIDA"} · {message.channel}</span><b>{message.subject || (message.direction === "inbound" ? "Respuesta recibida" : "Mensaje asistido")}</b><small>{message.contact_name || "Sin contacto"} · {message.invoice_folios.join(", ") || "Sin factura correlacionada"}</small></div><span className={`status-pill ${message.status}`}>{message.status}</span></header><pre>{message.body}</pre><footer><span>{message.direction === "inbound" ? `Origen: ${message.provider_payload?.sender || message.provider_payload?.provider || "registro manual"}` : `Seguridad: ${message.safety_status}${message.safety_flags.length ? ` · ${message.safety_flags.join(", ")}` : ""}`}</span><span>Costo: {message.cost_currency} {Number(message.llm_cost) + Number(message.messaging_cost)}</span>{message.attachment_names.length > 0 && <span>Adjuntos: {message.attachment_names.join(", ")}</span>}{message.provider_payload?.correlation?.needs_review && <span className="correlation-warning">Requiere revisión de correlación</span>}{message.provider_payload?.correlation?.unmatched_invoice_folios?.length > 0 && <span className="correlation-warning">Folios no encontrados: {message.provider_payload.correlation.unmatched_invoice_folios.join(", ")}</span>}{message.provider_payload?.correlation?.ambiguous_invoice_folios?.length > 0 && <span className="correlation-warning">Correlación ambigua: {message.provider_payload.correlation.ambiguous_invoice_folios.join(", ")}</span>}{message.provider_payload?.assisted_link && <span className="assisted-link">Enlace asistido generado y no abierto</span>}{["draft", "assisted_ready"].includes(message.status) && <button type="button" className="mini-button" disabled={busy} onClick={() => simulate(message)}>Simular entrega</button>}{message.status === "simulated" && <><button type="button" className="mini-button" disabled={busy} onClick={() => updateDelivery(message, "delivered")}>Marcar entregado</button><button type="button" className="mini-button danger" disabled={busy} onClick={() => updateDelivery(message, "failed")}>Marcar fallido</button></>}{message.status === "delivered" && <button type="button" className="mini-button" disabled={busy} onClick={() => updateDelivery(message, "read")}>Marcar leído</button>}</footer></article>)}{!messages.length && <p className="empty-version">Aún no hay mensajes preparados.</p>}</div></article>
    <aside className="communication-side"><article className="version-card"><p className="kicker">TRABAJOS DEL MOTOR</p><h3>Preparar comunicaciones</h3><div className="compact-list">{jobs.slice(0, 12).map((job) => <div key={job.id}><span><b>{job.action_type}</b><small>{job.stage} · {job.status}</small></span><button type="button" className="mini-button" disabled={busy || preparedJobIds.has(job.id)} onClick={() => prepare(job)}>{preparedJobIds.has(job.id) ? "Preparado" : "Preparar"}</button></div>)}{!jobs.length && <p className="empty-version">Ejecuta primero un ciclo del motor.</p>}</div></article><article className="version-card"><p className="kicker">E5-06</p><h3>Preferencias por contacto</h3><div className="compact-list">{contacts.map((contact) => <div key={contact.id}><span><b>{contact.name}</b><small>{contact.role}</small></span><div className="preference-buttons"><button type="button" className={contact.opted_out_email ? "mini-button danger" : "mini-button"} disabled={busy} onClick={() => optOut(contact, "email", !contact.opted_out_email)}>Email {contact.opted_out_email ? "bloqueado" : "activo"}</button><button type="button" className={contact.opted_out_whatsapp ? "mini-button danger" : "mini-button"} disabled={busy} onClick={() => optOut(contact, "whatsapp", !contact.opted_out_whatsapp)}>WA {contact.opted_out_whatsapp ? "bloqueado" : "activo"}</button></div></div>)}</div></article></aside>
    <article className="response-card"><div className="card-heading"><div><p className="kicker">E5-02 / E5-04</p><h3>Simular webhook entrante</h3></div><span className="read-only">Sólo local</span></div><form className="contract-form" onSubmit={recordInbound}><div className="form-grid"><label>Canal<select value={inboundForm.channel} onChange={(event) => { const channel = event.target.value; setInboundForm((current) => ({ ...current, channel, sender: channel === "email" ? contacts.find((contact) => contact.email)?.email || "" : contacts.find((contact) => contact.phone)?.phone || "" })); }}><option value="email">Email</option><option value="whatsapp">WhatsApp</option></select></label><label>ID proveedor simulado<input required value={inboundForm.provider_id} onChange={(event) => setInboundForm((current) => ({ ...current, provider_id: event.target.value }))} /></label><label>Remitente<input required value={inboundForm.sender} onChange={(event) => setInboundForm((current) => ({ ...current, sender: event.target.value }))} /></label><label>Hilo externo<input value={inboundForm.external_thread_key} onChange={(event) => setInboundForm((current) => ({ ...current, external_thread_key: event.target.value }))} placeholder="opcional" /></label><label>Respuesta a ID proveedor<input value={inboundForm.in_reply_to_provider_id} onChange={(event) => setInboundForm((current) => ({ ...current, in_reply_to_provider_id: event.target.value }))} placeholder="opcional" /></label><label>Folios separados por coma<input value={inboundForm.invoice_folios} onChange={(event) => setInboundForm((current) => ({ ...current, invoice_folios: event.target.value }))} /></label><label className="wide">Asunto<input disabled={inboundForm.channel !== "email"} value={inboundForm.subject} onChange={(event) => setInboundForm((current) => ({ ...current, subject: event.target.value }))} /></label><label className="wide">Respuesta<textarea required rows="4" value={inboundForm.body} onChange={(event) => setInboundForm((current) => ({ ...current, body: event.target.value }))} /></label><label className="wide">Adjuntos ficticios, uno por línea<textarea rows="3" value={inboundForm.attachment_names} onChange={(event) => setInboundForm((current) => ({ ...current, attachment_names: event.target.value }))} /></label></div><div className="button-row end"><button className="primary" disabled={busy}>Registrar entrada simulada</button></div></form></article>
    <article className="response-card"><div className="card-heading"><div><p className="kicker">E5-10</p><h3>Registrar respuesta manual</h3></div><span className="read-only">Teléfono u otro medio</span></div><form className="contract-form" onSubmit={recordManual}><div className="form-grid"><label>Factura<select required value={manualForm.invoice_id} onChange={(event) => { const invoice = invoices.find((item) => item.id === event.target.value); setManualForm((current) => ({ ...current, invoice_id: event.target.value, contact_id: contacts.find((contact) => contact.payer_id === invoice?.payer_id)?.id || "" })); }}>{invoices.map((invoice) => <option key={invoice.id} value={invoice.id}>{invoice.folio} · {invoice.payer_name}</option>)}</select></label><label>Contacto<select value={manualForm.contact_id} onChange={(event) => setManualForm((current) => ({ ...current, contact_id: event.target.value }))}><option value="">Sin contacto identificado</option>{eligibleManualContacts.map((contact) => <option key={contact.id} value={contact.id}>{contact.name}</option>)}</select></label><label>Medio<select value={manualForm.channel} onChange={(event) => setManualForm((current) => ({ ...current, channel: event.target.value }))}><option value="phone">Teléfono</option><option value="personal_email">Correo personal</option><option value="other">Otro</option></select></label><label>Asunto<input value={manualForm.subject} onChange={(event) => setManualForm((current) => ({ ...current, subject: event.target.value }))} /></label><label className="wide">Contenido recibido<textarea required rows="4" value={manualForm.body} onChange={(event) => setManualForm((current) => ({ ...current, body: event.target.value }))} /></label></div><div className="button-row end"><button className="secondary" disabled={busy || !manualForm.invoice_id}>Registrar respuesta</button></div></form></article>
    <article className="template-card"><div className="card-heading"><div><p className="kicker">PLANTILLAS VERSIONADAS</p><h3>Nueva versión</h3></div><span className="read-only">{templates.length} activas</span></div><form className="contract-form" onSubmit={saveTemplate}><div className="form-grid"><label>Acción<input value={form.template_key} onChange={(event) => setForm((current) => ({ ...current, template_key: event.target.value }))} /></label><label>Canal<select value={form.channel} onChange={(event) => setForm((current) => ({ ...current, channel: event.target.value }))}><option value="email">Email</option><option value="whatsapp_assisted">WhatsApp asistido</option></select></label><label>Etapa<select value={form.stage} onChange={(event) => setForm((current) => ({ ...current, stage: event.target.value }))}>{Object.keys(stageLabels).filter((stage) => stage !== "closed").map((stage) => <option key={stage} value={stage}>{stageLabels[stage]}</option>)}</select></label><label>Tono<select value={form.tone} onChange={(event) => setForm((current) => ({ ...current, tone: event.target.value }))}><option value="cordial">Cordial</option><option value="direct">Directo</option><option value="formal">Formal</option></select></label><label className="wide">Asunto<input disabled={form.channel !== "email"} value={form.subject_template} onChange={(event) => setForm((current) => ({ ...current, subject_template: event.target.value }))} /></label><label className="wide">Cuerpo<textarea rows="9" value={form.body_template} onChange={(event) => setForm((current) => ({ ...current, body_template: event.target.value }))} /></label><label className="check-inline"><input type="checkbox" checked={form.approved} onChange={(event) => setForm((current) => ({ ...current, approved: event.target.checked }))} /> Aprobada internamente</label></div><p className="form-help">Campos permitidos: recipient_name, client_name, sender_name, payer_name, invoice_summary, action_request, missing_items_section y bank_details_section.</p><div className="button-row end"><button className="primary" disabled={busy}>Guardar nueva versión</button></div></form></article>
  </section>;
}

const classificationLabels = {
  paid: "Ya pagó",
  payment_scheduled: "Pago programado",
  missing_oc_hes: "Falta OC / HES",
  supplier_data_issue: "Datos de proveedor",
  invoice_disputed: "Factura reclamada",
  payment_promise: "Promesa de pago",
  dispute: "Disputa",
  document_request: "Solicitud de documento",
  wrong_contact: "Contacto equivocado",
  other: "Otro",
};

function ExceptionsPanel({ clientId, request }) {
  const [cases, setCases] = useState([]);
  const [policies, setPolicies] = useState([]);
  const [evaluationSets, setEvaluationSets] = useState([]);
  const [evaluationReport, setEvaluationReport] = useState(null);
  const [proposals, setProposals] = useState([]);
  const [selected, setSelected] = useState(null);
  const [status, setStatus] = useState("open");
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState(null);
  const [review, setReview] = useState({ category: "other", extracted_data: "{}", human_minutes: "5", note: "" });
  const [checklistEdits, setChecklistEdits] = useState({});
  const [workflowStage, setWorkflowStage] = useState("");
  const [escalationNote, setEscalationNote] = useState("Solicito validar este caso antes de continuar la gestión.");
  const [proposalForm, setProposalForm] = useState({ proposed_changes: '{"payment_cycle":"Todos los viernes"}', rationale: "Dato observado en la respuesta y pendiente de aprobación." });
  const [responseForm, setResponseForm] = useState({ channel: "email", subject: "", body: "" });
  const [preparedResponse, setPreparedResponse] = useState(null);

  const load = useCallback(async () => {
    if (!clientId) return;
    try {
      const [rows, policyRows, setRows, proposalRows, report] = await Promise.all([
        request(`/api/v1/exceptions?client_id=${clientId}&status=${status}`),
        request(`/api/v1/classification-policies?client_id=${clientId}`),
        request(`/api/v1/evaluation/sets?client_id=${clientId}`),
        request(`/api/v1/payer-profile-proposals?client_id=${clientId}&status=`),
        request(`/api/v1/evaluation/report?client_id=${clientId}`),
      ]);
      setCases(rows);
      setPolicies(policyRows); setEvaluationSets(setRows); setProposals(proposalRows); setEvaluationReport(report);
      setSelected((current) => current && !rows.some((item) => item.id === current.id) ? null : current);
    } catch (error) { setNotice({ type: "error", text: error.message }); }
  }, [clientId, request, status]);

  useEffect(() => { load(); }, [load]);

  async function openCase(item) {
    setBusy(true); setNotice(null);
    try {
      const detail = await request(`/api/v1/exceptions/${item.id}?client_id=${clientId}`);
      const suggestion = detail.context.invoice && detail.context.message
        ? await request(`/api/v1/communications/exception-responses/${item.id}/suggestion?client_id=${clientId}`)
        : { channel: "email", subject: "", body: "" };
      setSelected(detail);
      setReview({ category: detail.classification?.category || "other", extracted_data: JSON.stringify(detail.classification?.extracted_data || {}, null, 2), human_minutes: "5", note: "" });
      setChecklistEdits(Object.fromEntries((detail.context.payability || []).map((check) => [check.id, check.status])));
      setWorkflowStage("");
      setResponseForm({ channel: suggestion.channel, subject: suggestion.subject || "", body: suggestion.body });
      setPreparedResponse(null);
    } catch (error) { setNotice({ type: "error", text: error.message }); } finally { setBusy(false); }
  }

  async function resolve(event) {
    event.preventDefault();
    if (!selected) return;
    setBusy(true); setNotice(null);
    try {
      const checklist_updates = (selected.context.payability || []).filter((item) => checklistEdits[item.id] && checklistEdits[item.id] !== item.status).map((item) => ({ item_id: item.id, status: checklistEdits[item.id], evidence: { ...item.evidence, source: "supervised_review" } }));
      const updated = await request(`/api/v1/exceptions/${selected.id}/review`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ client_id: clientId, category: review.category, extracted_data: JSON.parse(review.extracted_data || "{}"), human_minutes: Number(review.human_minutes), note: review.note || null, checklist_updates, workflow_stage: workflowStage || null }) });
      setSelected(updated);
      setNotice({ type: "success", text: `Revisión guardada como clasificación v${updated.classification.version}; no se ejecutó ninguna acción automática.` });
      await load();
    } catch (error) { setNotice({ type: "error", text: error.message }); } finally { setBusy(false); }
  }

  async function escalate() {
    if (!selected) return;
    setBusy(true); setNotice(null);
    try {
      const updated = await request(`/api/v1/exceptions/${selected.id}/escalate`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ client_id: clientId, note: escalationNote }) });
      setSelected(updated); setNotice({ type: "success", text: "Escalamiento local registrado; no se envió ninguna comunicación." }); await load();
    } catch (error) { setNotice({ type: "error", text: error.message }); } finally { setBusy(false); }
  }

  async function prepareResponse(event) {
    event.preventDefault();
    if (!selected) return;
    setBusy(true); setNotice(null);
    try {
      const message = await request(`/api/v1/communications/exception-responses/${selected.id}/draft`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ client_id: clientId, channel: responseForm.channel, subject: responseForm.channel === "email" ? responseForm.subject || null : null, body: responseForm.body }) });
      setPreparedResponse(message);
      setNotice({ type: message.status === "blocked" ? "error" : "success", text: message.status === "blocked" ? `El borrador quedó bloqueado: ${message.safety_flags.join(", ")}.` : "Respuesta preparada en la bandeja de salida; no se realizó ningún envío externo." });
    } catch (error) { setNotice({ type: "error", text: error.message }); } finally { setBusy(false); }
  }

  function exportEvaluationReport() {
    if (!evaluationReport) return;
    const columns = ["category", "predicted_count", "actual_count", "correct_count", "error_count", "false_negative_count", "precision", "recall", "mode", "eligible_for_automation", "permanent_supervision"];
    const escape = (value) => `"${String(value ?? "").replaceAll('"', '""')}"`;
    const csv = [columns.join(","), ...evaluationReport.categories.map((row) => columns.map((column) => escape(row[column])).join(","))].join("\n");
    const url = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
    const link = document.createElement("a");
    link.href = url; link.download = `evaluacion-g2-${clientId}.csv`; link.click(); URL.revokeObjectURL(url);
  }

  async function freezeSet(evaluationSet) {
    setBusy(true); setNotice(null);
    try {
      await request(`/api/v1/evaluation/sets/${evaluationSet.id}/freeze?client_id=${clientId}`, { method: "POST" });
      setNotice({ type: "success", text: `Set de evaluación v${evaluationSet.version} congelado.` }); await load();
    } catch (error) { setNotice({ type: "error", text: error.message }); } finally { setBusy(false); }
  }

  async function changePolicy(policy, mode) {
    setBusy(true); setNotice(null);
    try {
      await request(`/api/v1/classification-policies/${policy.id}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ client_id: clientId, mode }) });
      setNotice({ type: "success", text: `${classificationLabels[policy.category]} quedó en modo ${mode}.` }); await load();
    } catch (error) { setNotice({ type: "error", text: error.message }); } finally { setBusy(false); }
  }

  async function createProposal(event) {
    event.preventDefault();
    if (!selected) return;
    setBusy(true); setNotice(null);
    try {
      await request("/api/v1/payer-profile-proposals", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ client_id: clientId, exception_id: selected.id, proposed_changes: JSON.parse(proposalForm.proposed_changes), rationale: proposalForm.rationale }) });
      setNotice({ type: "success", text: "Propuesta creada; la ficha aún no fue modificada." }); await load();
    } catch (error) { setNotice({ type: "error", text: error.message }); } finally { setBusy(false); }
  }

  async function decideProposal(proposal, decision) {
    setBusy(true); setNotice(null);
    try {
      await request(`/api/v1/payer-profile-proposals/${proposal.id}/decision`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ client_id: clientId, decision, note: "Decisión desde consola supervisada" }) });
      setNotice({ type: "success", text: `Propuesta ${decision === "approved" ? "aprobada y versionada" : "rechazada"}.` }); await load();
    } catch (error) { setNotice({ type: "error", text: error.message }); } finally { setBusy(false); }
  }

  return <section className="exceptions-layout">
    <Message value={notice} onClose={() => setNotice(null)} />
    <article className="exception-queue"><div className="card-heading"><div><p className="kicker">E6-02 / E6-04 / E7-01</p><h3>Bandeja priorizada</h3></div><div className="queue-actions"><select value={status} onChange={(event) => { setStatus(event.target.value); setSelected(null); }}><option value="open">Abiertas</option><option value="resolved">Resueltas</option></select><button type="button" className="ghost" onClick={load}>Actualizar</button></div></div><div className="exception-list">{cases.map((item) => <button type="button" key={item.id} className={selected?.id === item.id ? "exception-item selected" : "exception-item"} onClick={() => openCase(item)}><span className={`priority-badge p${Math.floor(item.priority / 20)}`}>{item.priority}</span><span><b>{classificationLabels[item.classification?.category] || item.classification?.category || item.kind}</b><small>{item.context.invoice?.folio || "Sin factura"} · {item.context.invoice?.payer_name || item.kind}</small><em>{item.context.message?.body || "Sin contenido"}</em></span><span className="confidence">{item.classification ? `${Math.round(Number(item.classification.confidence) * 100)}%` : "—"}</span></button>)}{!cases.length && <p className="empty-version">No hay excepciones {status === "open" ? "abiertas" : "resueltas"}.</p>}</div></article>
    <aside className="exception-detail">{selected ? <>
      <article className="version-card"><p className="kicker">PRIORIDAD {selected.priority} · {selected.kind}</p><h3>{classificationLabels[selected.classification?.category] || selected.classification?.category}</h3><div className="case-meta"><span>Confianza <b>{Math.round(Number(selected.classification?.confidence || 0) * 100)}%</b></span><span>Versión <b>{selected.classification?.version}</b></span><span>Origen <b>{selected.classification?.classifier_kind}</b></span></div><blockquote>{selected.context.message?.body}</blockquote>{selected.detail?.client_response && <div className="client-response operator-response"><b>Respuesta de la pyme · {selected.detail.client_response.response_type}</b><span>{selected.detail.client_response.message}</span><small>{new Date(selected.detail.client_response.submitted_at).toLocaleString("es-CL")}</small></div>}{selected.context.invoice && <div className="invoice-context"><b>{selected.context.invoice.folio}</b><span>{selected.context.invoice.payer_name}</span><span>{money.format(Number(selected.context.invoice.total_amount))} · vence {selected.context.invoice.due_on}</span></div>}<div className="extraction-grid"><div><b>Fechas</b><span>{selected.classification?.extracted_data?.payment_dates?.join(", ") || "—"}</span></div><div><b>Montos</b><span>{selected.classification?.extracted_data?.amounts?.map((amount) => money.format(amount)).join(", ") || "—"}</span></div><div><b>OC</b><span>{selected.classification?.extracted_data?.purchase_orders?.join(", ") || "—"}</span></div><div><b>HES</b><span>{selected.classification?.extracted_data?.hes_numbers?.join(", ") || "—"}</span></div></div></article>
      {selected.status === "open" ? <>
        {selected.context.invoice && selected.context.message && <article className="review-card response-draft-card"><p className="kicker">E7-03 · RESPUESTA ASISTIDA</p><h3>Preparar respuesta segura</h3><form onSubmit={prepareResponse}><label>Canal<select value={responseForm.channel} onChange={(event) => setResponseForm((current) => ({ ...current, channel: event.target.value }))}><option value="email">Email</option><option value="whatsapp_assisted">WhatsApp asistido</option></select></label>{responseForm.channel === "email" && <label>Asunto<input value={responseForm.subject} onChange={(event) => setResponseForm((current) => ({ ...current, subject: event.target.value }))} /></label>}<label>Contenido<textarea required minLength="10" rows="8" value={responseForm.body} onChange={(event) => setResponseForm((current) => ({ ...current, body: event.target.value }))} /></label><button className="secondary" disabled={busy || !responseForm.body}>Crear borrador</button></form><p className="form-help">Se guarda en la bandeja de salida con revisión humana obligatoria y sin entrega externa.</p>{preparedResponse && <div className="prepared-response"><b>{preparedResponse.status === "blocked" ? "Borrador bloqueado" : "Borrador preparado"}</b><span>{preparedResponse.channel} · {preparedResponse.status} · costo $0</span></div>}</article>}
        <article className="review-card"><p className="kicker">E7-03 / E7-05</p><h3>Decisión humana</h3><form onSubmit={resolve}><label>Categoría<select value={review.category} onChange={(event) => setReview((current) => ({ ...current, category: event.target.value }))}>{Object.entries(classificationLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label><label>Datos extraídos (JSON)<textarea rows="8" value={review.extracted_data} onChange={(event) => setReview((current) => ({ ...current, extracted_data: event.target.value }))} /></label>{selected.context.payability?.length > 0 && <fieldset className="checklist-corrections"><legend>Correcciones de checklist</legend>{selected.context.payability.map((item) => <label key={item.id}>{item.label}<select value={checklistEdits[item.id] || item.status} onChange={(event) => setChecklistEdits((current) => ({ ...current, [item.id]: event.target.value }))}><option value="pending">Pendiente</option><option value="requested">Solicitado</option><option value="fulfilled">Cumplido</option><option value="not_applicable">No aplica</option><option value="blocked">Bloqueado</option></select></label>)}</fieldset>}<label>Corregir etapa<select value={workflowStage} onChange={(event) => setWorkflowStage(event.target.value)}><option value="">Sin cambio</option>{Object.entries(stageLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label><label>Minutos humanos<input type="number" min="0" max="480" step="0.25" value={review.human_minutes} onChange={(event) => setReview((current) => ({ ...current, human_minutes: event.target.value }))} /></label><label>Nota de revisión<textarea rows="3" value={review.note} onChange={(event) => setReview((current) => ({ ...current, note: event.target.value }))} /></label><button className="primary" disabled={busy}>Confirmar y resolver</button></form></article>
        <article className="review-card"><p className="kicker">E7-04</p><h3>Escalar localmente</h3><label>Nota para la pyme<textarea rows="3" value={escalationNote} onChange={(event) => setEscalationNote(event.target.value)} /></label><button type="button" className="secondary" disabled={busy} onClick={escalate}>Registrar escalamiento</button><p className="form-help">No envía correo ni WhatsApp.</p></article>
        {selected.context.invoice && <article className="review-card"><p className="kicker">EP-09</p><h3>Proponer cambio de ficha</h3><form onSubmit={createProposal}><label>Cambios propuestos (JSON)<textarea rows="4" value={proposalForm.proposed_changes} onChange={(event) => setProposalForm((current) => ({ ...current, proposed_changes: event.target.value }))} /></label><label>Fundamento<textarea rows="3" value={proposalForm.rationale} onChange={(event) => setProposalForm((current) => ({ ...current, rationale: event.target.value }))} /></label><button className="secondary" disabled={busy}>Crear propuesta</button></form></article>}
      </> : <article className="review-card resolved-review"><p className="kicker">RESUELTA</p><h3>{selected.resolution?.decision === "corrected" ? "Clasificación corregida" : "Clasificación confirmada"}</h3><p>{selected.resolution?.note || "Sin nota de revisión."}</p><span>{selected.human_minutes} minutos humanos acumulados</span></article>}
      <article className="version-card"><p className="kicker">CONTEXTO OPERATIVO</p><h3>Checklist e historial</h3><div className="compact-list">{selected.context.payability?.map((item) => <div key={item.id}><span><b>{item.label}</b><small>{item.responsible_role}</small></span><span className={`status-pill ${item.status}`}>{item.status}</span></div>)}</div><p className="history-count">{selected.context.events?.length || 0} eventos auditables · {selected.context.classification_history?.length || 0} versiones de clasificación</p></article>
    </> : <article className="version-card empty-detail"><p className="kicker">REVISIÓN SUPERVISADA</p><h3>Selecciona un caso</h3><p>Verás la respuesta, factura, extracción, checklist y trazabilidad antes de confirmar cualquier decisión.</p></article>}</aside>
    <section className="supervision-dashboard"><article className="policy-card"><div className="card-heading"><div><p className="kicker">E6-07 / E6-09</p><h3>Precisión y puerta de automatización</h3></div><span className="read-only">Mínimo 90% · 20 muestras</span></div><div className="policy-grid">{policies.map((policy) => <div key={policy.id}><span><b>{classificationLabels[policy.category]}</b><small>{policy.sample_count} muestras · {policy.current_precision == null ? "sin medición" : `${Math.round(Number(policy.current_precision) * 100)}% precisión`}</small></span><button type="button" className={policy.eligible_for_automation ? "mini-button" : "mini-button danger"} disabled={busy || !policy.eligible_for_automation} onClick={() => changePolicy(policy, policy.mode === "automatic" ? "supervised" : "automatic")}>{policy.mode === "automatic" ? "Automática" : policy.eligible_for_automation ? "Habilitar" : "Supervisada"}</button></div>)}</div></article><article className="evaluation-card"><div className="card-heading"><div><p className="kicker">SET VERSIONADO</p><h3>Evaluación anonimizada</h3></div></div><div className="compact-list">{evaluationSets.map((item) => <div key={item.id}><span><b>Versión {item.version} · {item.status}</b><small>{item.sample_count} ejemplos · {item.anonymization_version}</small></span>{item.status === "open" && <button type="button" className="mini-button" disabled={busy || item.sample_count === 0} onClick={() => freezeSet(item)}>Congelar</button>}</div>)}{!evaluationSets.length && <p className="empty-version">Las revisiones humanas crearán el primer set.</p>}</div><h4>Propuestas de ficha</h4><div className="compact-list">{proposals.map((proposal) => <div key={proposal.id}><span><b>{proposal.status}</b><small>{proposal.rationale}</small></span>{proposal.status === "pending" && <div className="preference-buttons"><button type="button" className="mini-button" onClick={() => decideProposal(proposal, "approved")}>Aprobar</button><button type="button" className="mini-button danger" onClick={() => decideProposal(proposal, "rejected")}>Rechazar</button></div>}</div>)}{!proposals.length && <p className="empty-version">Sin propuestas.</p>}</div></article>{evaluationReport && <article className="g2-report-card"><div className="card-heading"><div><p className="kicker">PUERTA G2</p><h3>Reporte de desempeño supervisado</h3></div><button type="button" className="secondary" onClick={exportEvaluationReport}>Exportar CSV</button></div><div className="g2-summary"><span><b>{evaluationReport.total_examples}</b><small>ejemplos reales</small></span><span><b>{evaluationReport.error_count}</b><small>errores</small></span><span><b>{evaluationReport.reviewed_cases}</b><small>casos revisados</small></span><span><b>{evaluationReport.total_human_minutes}</b><small>minutos humanos</small></span></div><div className="report-table"><div className="report-row report-head"><span>Categoría</span><span>Precisión</span><span>Recall</span><span>Errores</span><span>Decisión</span></div>{evaluationReport.categories.map((row) => <div className="report-row" key={row.category}><span>{classificationLabels[row.category]}</span><span>{row.precision == null ? "—" : `${Math.round(Number(row.precision) * 100)}%`}</span><span>{row.recall == null ? "—" : `${Math.round(Number(row.recall) * 100)}%`}</span><span>{row.error_count} / {row.false_negative_count}</span><span>{row.permanent_supervision ? "Siempre supervisada" : row.eligible_for_automation ? "Elegible" : "Supervisada"}</span></div>)}</div></article>}</section>
  </section>;
}

function PaymentsPanel({ clientId, invoices, request, onChanged }) {
  const [payments, setPayments] = useState([]);
  const [transactions, setTransactions] = useState([]);
  const [proposals, setProposals] = useState([]);
  const [commissionReport, setCommissionReport] = useState(null);
  const [reportPeriod, setReportPeriod] = useState(new Date().toISOString().slice(0, 7));
  const [statementFile, setStatementFile] = useState(null);
  const [statementPreview, setStatementPreview] = useState(null);
  const [evidenceFile, setEvidenceFile] = useState(null);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState(null);
  const [manual, setManual] = useState({ invoice_id: "", amount: "", paid_on: new Date().toISOString().slice(0, 10), reference: "" });

  const load = useCallback(async () => {
    if (!clientId) return;
    try {
      const [paymentRows, transactionRows, proposalRows, report] = await Promise.all([
        request(`/api/v1/payments?client_id=${clientId}`),
        request(`/api/v1/payments/bank-transactions?client_id=${clientId}`),
        request(`/api/v1/payments/reconciliation-proposals?client_id=${clientId}`),
        request(`/api/v1/payments/commission-report?client_id=${clientId}&period=${reportPeriod}`),
      ]);
      setPayments(paymentRows); setTransactions(transactionRows); setProposals(proposalRows);
      setCommissionReport(report);
      setManual((current) => ({ ...current, invoice_id: current.invoice_id || invoices.find((invoice) => invoice.status !== "paid" && invoice.status !== "void")?.id || "" }));
    } catch (error) { setNotice({ type: "error", text: error.message }); }
  }, [clientId, invoices, reportPeriod, request]);

  useEffect(() => { load(); }, [load]);

  async function saveManual(event) {
    event.preventDefault();
    if (!evidenceFile) { setNotice({ type: "error", text: "Selecciona un comprobante." }); return; }
    setBusy(true); setNotice(null);
    const form = new FormData();
    form.append("client_id", clientId); form.append("invoice_id", manual.invoice_id); form.append("amount", manual.amount); form.append("paid_on", manual.paid_on); form.append("reference", manual.reference); form.append("evidence", evidenceFile);
    try {
      const payment = await request("/api/v1/payments/manual", { method: "POST", body: form });
      setNotice({ type: "success", text: `Pago verificado por ${money.format(Number(payment.amount))}; evidencia registrada.` });
      setEvidenceFile(null); setManual((current) => ({ ...current, amount: "", reference: "" }));
      await load(); await onChanged();
    } catch (error) { setNotice({ type: "error", text: error.message }); } finally { setBusy(false); }
  }

  async function sendStatement(commit) {
    if (!statementFile) return;
    setBusy(true); setNotice(null);
    const form = new FormData(); form.append("client_id", clientId); form.append("commit", String(commit)); form.append("file", statementFile);
    try {
      const result = await request("/api/v1/payments/bank-statements", { method: "POST", body: form });
      setStatementPreview(result);
      if (commit) { setNotice({ type: "success", text: `${result.imported_count} movimientos importados y ${result.proposals_created} propuestas creadas.` }); await load(); }
    } catch (error) { setNotice({ type: "error", text: error.message }); } finally { setBusy(false); }
  }

  async function decide(proposal, decision) {
    setBusy(true); setNotice(null);
    try {
      await request(`/api/v1/payments/reconciliation-proposals/${proposal.id}/decision`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ client_id: clientId, decision, note: `Decisión ${decision} desde consola local` }) });
      setNotice({ type: "success", text: decision === "confirmed" ? "Conciliación confirmada y pago verificado." : "Propuesta rechazada sin registrar pago." });
      await load(); await onChanged();
    } catch (error) { setNotice({ type: "error", text: error.message }); } finally { setBusy(false); }
  }

  function exportCommissionReport() {
    if (!commissionReport) return;
    const header = ["periodo", "pago_id", "folio", "fecha_pago", "monto_pago_clp", "origen", "atribucion", "porcentaje", "comision_clp", "contrato_id"];
    const rows = commissionReport.details.map((item) => [commissionReport.period, item.payment_id, item.folio || "", item.paid_on, item.payment_amount, item.source, item.category, item.percentage, item.commission_amount, item.contract_id || ""]);
    const csv = [header, ...rows].map((row) => row.map((value) => `"${String(value).replaceAll('"', '""')}"`).join(",")).join("\n");
    const url = URL.createObjectURL(new Blob(["\ufeff", csv], { type: "text/csv;charset=utf-8" }));
    const anchor = document.createElement("a"); anchor.href = url; anchor.download = `comisiones-${commissionReport.period}.csv`; anchor.click(); URL.revokeObjectURL(url);
  }

  return <section className="payments-layout">
    <Message value={notice} onClose={() => setNotice(null)} />
    <article className="payment-card"><div className="card-heading"><div><p className="kicker">E8-02 / E9-01</p><h3>Registrar pago manual</h3></div><span className="read-only">Con evidencia obligatoria</span></div><form className="payment-form" onSubmit={saveManual}><label>Factura<select required value={manual.invoice_id} onChange={(event) => setManual((current) => ({ ...current, invoice_id: event.target.value }))}><option value="">Seleccionar</option>{invoices.filter((invoice) => !["paid", "void"].includes(invoice.status)).map((invoice) => <option key={invoice.id} value={invoice.id}>{invoice.folio} · {invoice.payer_name} · {money.format(Number(invoice.total_amount))}</option>)}</select></label><label>Monto<input required type="number" min="1" step="0.01" value={manual.amount} onChange={(event) => setManual((current) => ({ ...current, amount: event.target.value }))} /></label><label>Fecha de pago<input required type="date" value={manual.paid_on} onChange={(event) => setManual((current) => ({ ...current, paid_on: event.target.value }))} /></label><label>Referencia única<input required minLength="2" value={manual.reference} onChange={(event) => setManual((current) => ({ ...current, reference: event.target.value }))} placeholder="N° comprobante" /></label><label className="wide">Comprobante<input required type="file" onChange={(event) => setEvidenceFile(event.target.files?.[0] || null)} /></label><button className="primary" disabled={busy}>Registrar y verificar</button></form></article>
    <article className="payment-card"><div className="card-heading"><div><p className="kicker">E8-03 / E8-04</p><h3>Importar cartola local</h3></div><span className="file-type">CSV · XLSX</span></div><div className="statement-import"><input type="file" accept=".csv,.xlsx,.xlsm" onChange={(event) => { setStatementFile(event.target.files?.[0] || null); setStatementPreview(null); }} /><div className="button-row"><button type="button" className="secondary" disabled={busy || !statementFile} onClick={() => sendStatement(false)}>Validar</button><button type="button" className="primary" disabled={busy || !statementPreview?.can_commit} onClick={() => sendStatement(true)}>Importar y proponer</button></div>{statementPreview && <div className="import-summary"><b>{statementPreview.valid_rows.length} movimientos válidos</b><span>{statementPreview.issues.length ? `${statementPreview.issues.length} errores` : "Sin errores"}</span>{statementPreview.issues.map((issue, index) => <small key={`${issue.row}-${index}`}>Fila {issue.row}: {issue.message}</small>)}</div>}<p className="form-help">Usa el archivo ficticio data/demo/imports/cartola-cordillera.csv. No existe conexión bancaria.</p></div></article>
    <article className="reconciliation-card"><div className="card-heading"><div><p className="kicker">E8-04 / E8-05</p><h3>Propuestas de conciliación</h3></div><span className="read-only">Revisión humana obligatoria</span></div><div className="proposal-list">{proposals.map((proposal) => <article key={proposal.id}><div className="proposal-score"><b>{Math.round(Number(proposal.score))}</b><small>puntos</small></div><div><b>{proposal.transaction.external_id} · {money.format(Number(proposal.transaction.amount))}</b><span>{proposal.transaction.occurred_on} · RUT {proposal.transaction.counterparty_rut || "no informado"}</span><small>{proposal.invoices.map((invoice) => `${invoice.folio} (${money.format(Number(invoice.allocated_amount))})`).join(" + ")}</small></div><span className={`status-pill ${proposal.status}`}>{proposal.status}</span>{proposal.status === "pending" && <div className="preference-buttons"><button type="button" className="mini-button" disabled={busy} onClick={() => decide(proposal, "confirmed")}>Confirmar</button><button type="button" className="mini-button danger" disabled={busy} onClick={() => decide(proposal, "rejected")}>Rechazar</button></div>}</article>)}{!proposals.length && <p className="empty-version">Aún no hay propuestas.</p>}</div></article>
    <article className="commission-card"><div className="card-heading"><div><p className="kicker">E9-02 / E9-03</p><h3>Comisiones y métricas</h3></div><div className="commission-actions"><input type="month" value={reportPeriod} onChange={(event) => setReportPeriod(event.target.value)} /><button type="button" className="secondary" disabled={!commissionReport} onClick={exportCommissionReport}>Exportar CSV</button></div></div>{commissionReport && <><div className="g2-summary"><span><b>{money.format(Number(commissionReport.totals.verified_amount))}</b><small>pagos verificados</small></span><span><b>{money.format(Number(commissionReport.totals.commission_amount))}</b><small>comisión calculada</small></span><span><b>{commissionReport.metrics.managed_invoices}</b><small>facturas gestionadas</small></span><span><b>{commissionReport.metrics.human_minutes}</b><small>minutos humanos</small></span></div><div className="commission-detail"><div className="commission-row commission-head"><span>Factura</span><span>Regla</span><span>Base</span><span>%</span><span>Comisión</span></div>{commissionReport.details.map((item) => <div className="commission-row" key={item.payment_id}><span>{item.folio || item.invoice_id}</span><span>{item.category === "preventive_on_time" ? "Preventiva a tiempo" : item.category === "arrears_recovery" ? "Recuperación en mora" : "No atribuible"}</span><span>{money.format(Number(item.payment_amount))}</span><span>{item.percentage}%</span><span>{money.format(Number(item.commission_amount))}</span></div>)}{!commissionReport.details.length && <p className="empty-version">Sin pagos verificados en el período.</p>}</div><p className="commission-note">Costo IA USD {commissionReport.metrics.llm_cost_usd} · mensajería USD {commissionReport.metrics.messaging_cost_usd}. No se mezclan monedas sin un tipo de cambio auditado.</p></>}</article>
    <article className="payment-history-card"><div className="card-heading"><div><p className="kicker">TRAZABILIDAD</p><h3>Pagos verificados</h3></div><span className="read-only">{payments.length} registros</span></div><div className="compact-list">{payments.map((payment) => { const invoice = invoices.find((item) => item.id === payment.invoice_id); return <div key={payment.id}><span><b>{invoice?.folio || payment.invoice_id}</b><small>{payment.paid_on} · {payment.source} · {payment.reference}</small></span><b>{money.format(Number(payment.amount))}</b></div>; })}{!payments.length && <p className="empty-version">Sin pagos registrados.</p>}</div><h4>Movimientos importados</h4><div className="compact-list">{transactions.map((transaction) => <div key={transaction.id}><span><b>{transaction.external_id}</b><small>{transaction.occurred_on} · {transaction.counterparty_rut || "sin RUT"}</small></span><span className={`status-pill ${transaction.status}`}>{transaction.status}</span></div>)}</div></article>
  </section>;
}

function AccessLogsPanel({ request }) {
  const [logs, setLogs] = useState([]);
  const [notice, setNotice] = useState(null);
  const [limit, setLimit] = useState(100);

  const load = useCallback(async () => {
    try { setLogs(await request(`/api/v1/access-logs?limit=${limit}`)); }
    catch (error) { setNotice({ type: "error", text: error.message }); }
  }, [limit, request]);

  useEffect(() => { load(); }, [load]);
  const failures = logs.filter((item) => item.status_code >= 400).length;
  const users = new Set(logs.map((item) => item.user_id)).size;
  const average = logs.length ? Math.round(logs.reduce((sum, item) => sum + item.duration_ms, 0) / logs.length) : 0;
  return <section className="access-layout">
    <Message value={notice} onClose={() => setNotice(null)} />
    <section className="stats-grid access-stats"><Stat label="Accesos registrados" value={logs.length} note={`últimos ${limit}`} /><Stat label="Usuarios" value={users} note="identidades distintas" /><Stat label="Respuestas con error" value={failures} note="estado HTTP 4xx/5xx" /><Stat label="Duración media" value={`${average} ms`} note="tiempo de respuesta" /></section>
    <article className="access-card"><div className="card-heading"><div><p className="kicker">E12-03 · LEDGER INMUTABLE</p><h3>Accesos a datos</h3></div><div className="queue-actions"><select value={limit} onChange={(event) => setLimit(Number(event.target.value))}><option value="50">50 registros</option><option value="100">100 registros</option><option value="250">250 registros</option></select><button type="button" className="ghost" onClick={load}>Actualizar</button></div></div><div className="table-wrap"><table><thead><tr><th>Fecha</th><th>Usuario / rol</th><th>Cliente</th><th>Solicitud</th><th>Estado</th><th>Duración</th><th>Solicitud ID</th></tr></thead><tbody>{logs.map((item) => <tr key={item.id}><td>{new Date(item.created_at).toLocaleString("es-CL")}</td><td><b>{item.actor_role}</b><small>{item.user_id.slice(0, 8)}…</small></td><td><small>{item.client_id ? `${item.client_id.slice(0, 8)}…` : "sin alcance"}</small></td><td><b>{item.method}</b><small>{item.path}</small></td><td><span className={`status-pill ${item.status_code < 400 ? "matched" : "rejected"}`}>{item.status_code}</span></td><td>{item.duration_ms} ms</td><td><small>{item.request_id}</small></td></tr>)}{!logs.length && <tr><td colSpan="7" className="empty">Aún no hay accesos autenticados registrados.</td></tr>}</tbody></table></div><p className="access-note">No se almacenan tokens ni cuerpos de solicitudes. El origen se conserva únicamente como hash seudonimizado.</p></article>
  </section>;
}

function DocumentUploadDialog({ invoice, request, onClose, onUploaded }) {
  const [checklist, setChecklist] = useState(null);
  const [itemId, setItemId] = useState("");
  const [file, setFile] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    request(`/api/v1/payability/invoices/${invoice.id}`).then((result) => {
      setChecklist(result);
      const available = result.items.filter((item) => item.required && item.responsible_role === "client" && !["fulfilled", "not_applicable"].includes(item.status));
      setItemId(available[0]?.id || "");
    }).catch((requestError) => setError(requestError.message));
  }, [invoice.id, request]);

  const availableItems = checklist?.items?.filter((item) => item.required && item.responsible_role === "client" && !["fulfilled", "not_applicable"].includes(item.status)) || [];

  async function submit(event) {
    event.preventDefault();
    if (!file || !itemId) return;
    setBusy(true); setError("");
    const body = new FormData();
    body.append("invoice_id", invoice.id); body.append("payability_item_id", itemId); body.append("document", file);
    try {
      const submission = await request("/api/v1/client-portal/documents", { method: "POST", body });
      onUploaded(submission);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
    }
  }

  return <div className="modal-backdrop" role="presentation"><section className="modal compact-modal" role="dialog" aria-modal="true" aria-labelledby="document-upload-title"><div className="card-heading"><div><p className="kicker">E10-03 · CARGA SEGURA</p><h2 id="document-upload-title">Documento para {invoice.folio}</h2></div><button type="button" className="icon-button" onClick={onClose} aria-label="Cerrar">×</button></div><form className="pause-form" onSubmit={submit}><label>Requisito<select required value={itemId} onChange={(event) => setItemId(event.target.value)}><option value="">Selecciona un requisito</option>{availableItems.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}</select></label><label>Archivo<input required type="file" accept=".pdf,.png,.jpg,.jpeg,.txt,.csv,.xlsx" onChange={(event) => setFile(event.target.files?.[0] || null)} /></label><p className="form-help">Máximo 10 MB. El contenido se cifra antes de almacenarse y queda pendiente de revisión humana.</p>{error && <p className="field-error">{error}</p>}{checklist && !availableItems.length && <p className="success-line">No hay requisitos documentales pendientes de la pyme.</p>}<div className="button-row end"><button type="button" className="ghost" onClick={onClose}>Cancelar</button><button className="primary" disabled={busy || !file || !itemId}>{busy ? "Cifrando…" : "Enviar a revisión"}</button></div></form></section></div>;
}

function ClientPortalPanel({ clientId, userRole, request, download, onOpenChecklist }) {
  const [asOf, setAsOf] = useState(new Date().toISOString().slice(0, 10));
  const [summary, setSummary] = useState(null);
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState(null);
  const [submissions, setSubmissions] = useState([]);
  const [reviewNotes, setReviewNotes] = useState({});
  const [reviewing, setReviewing] = useState("");
  const [documentTarget, setDocumentTarget] = useState(null);
  const [clientTrend, setClientTrend] = useState(null);
  const [escalations, setEscalations] = useState([]);
  const [escalationReplies, setEscalationReplies] = useState({});
  const [responding, setResponding] = useState("");

  const query = useCallback((dateField) => {
    const params = new URLSearchParams({ [dateField]: asOf });
    if (userRole !== "client") params.set("client_id", clientId);
    return params.toString();
  }, [asOf, clientId, userRole]);

  const load = useCallback(async () => {
    if (!clientId) return;
    setLoading(true); setMessage(null);
    try {
      const calls = [
        request(`/api/v1/client-portal/summary?${query("as_of")}`),
        request(`/api/v1/client-portal/weekly-report?${query("week_ending")}`),
      ];
      if (userRole === "client") {
        const start = new Date(`${asOf}T12:00:00`); start.setDate(start.getDate() - 83);
        calls.push(request(`/api/v1/metrics/client-trend?date_from=${start.toISOString().slice(0, 10)}&date_to=${asOf}`));
        calls.push(request("/api/v1/client-portal/escalated-exceptions"));
      } else {
        calls.push(request(`/api/v1/client-portal/document-submissions?client_id=${clientId}&status=pending`));
      }
      const [summaryResult, reportResult, thirdResult, fourthResult = []] = await Promise.all(calls);
      setSummary(summaryResult); setReport(reportResult);
      if (userRole === "client") { setClientTrend(thirdResult); setEscalations(fourthResult); setSubmissions([]); }
      else { setSubmissions(thirdResult || []); setClientTrend(null); setEscalations([]); }
    } catch (error) {
      setMessage({ type: "error", text: error.message });
    } finally {
      setLoading(false);
    }
  }, [clientId, query, request]);

  useEffect(() => { load(); }, [load]);

  async function exportReport() {
    try {
      await download(`/api/v1/client-portal/weekly-report.csv?${query("week_ending")}`, `reporte-semanal-${asOf}.csv`);
      setMessage({ type: "success", text: "Reporte semanal exportado en CSV." });
    } catch (error) {
      setMessage({ type: "error", text: error.message });
    }
  }

  async function reviewDocument(submission, decision) {
    const note = (reviewNotes[submission.id] || "").trim();
    if (decision === "rejected" && !note) { setMessage({ type: "error", text: "Indica el motivo antes de rechazar el documento." }); return; }
    setReviewing(submission.id); setMessage(null);
    try {
      await request(`/api/v1/client-portal/document-submissions/${submission.id}/review`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ client_id: clientId, decision, note: note || null }) });
      setMessage({ type: "success", text: decision === "accepted" ? "Documento aceptado y requisito completado." : "Documento rechazado; el requisito continúa abierto." });
      await load();
    } catch (error) {
      setMessage({ type: "error", text: error.message });
    } finally {
      setReviewing("");
    }
  }

  async function respondToEscalation(item, responseType) {
    const reply = (escalationReplies[item.id] || "").trim();
    if (reply.length < 3) { setMessage({ type: "error", text: "Escribe una respuesta de al menos 3 caracteres." }); return; }
    setResponding(item.id); setMessage(null);
    try {
      await request(`/api/v1/client-portal/escalated-exceptions/${item.id}/response`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ response_type: responseType, message: reply }) });
      setMessage({ type: "success", text: "Respuesta registrada y enviada a la bandeja del operador." });
      await load();
    } catch (error) { setMessage({ type: "error", text: error.message }); }
    finally { setResponding(""); }
  }

  const totals = summary?.totals;
  return <section className="client-portal-layout">
    <Message value={message} onClose={() => setMessage(null)} />
    <article className="report-hero">
      <div><p className="kicker">E10-01 / E10-02 · SOLO LECTURA</p><h3>{summary?.client_name || "Resumen del cliente"}</h3><p>Estado verificable de facturas, pagos y requisitos documentales al cierre seleccionado.</p></div>
      <div className="report-controls"><label>Fecha de corte<input type="date" value={asOf} onChange={(event) => setAsOf(event.target.value)} /></label><button type="button" className="secondary" onClick={load} disabled={loading}>{loading ? "Actualizando…" : "Actualizar"}</button><button type="button" className="primary" onClick={exportReport} disabled={!report}>Descargar reporte semanal</button></div>
    </article>
    {report && <article className="weekly-strip"><div><span>Semana informada</span><b>{report.period_start} al {report.period_end}</b></div><div><span>Pagos verificados en la semana</span><b>{report.payments_this_week_count} · {money.format(Number(report.payments_this_week_amount))}</b></div><small>El envío por correo queda en modo local hasta disponer de infraestructura externa autorizada.</small></article>}
    <section className="stats-grid" aria-label="Resumen para la pyme">
      <Stat label="Facturas gestionadas" value={totals?.invoice_count ?? "—"} note={totals ? money.format(Number(totals.managed_amount)) : "cargando"} />
      <Stat label="Pagables" value={totals?.payable_count ?? "—"} note="checklist completo" />
      <Stat label="En riesgo" value={totals?.at_risk_count ?? "—"} note="incluye reclamadas" />
      <Stat label="Pagadas" value={totals?.paid_count ?? "—"} note={totals ? money.format(Number(totals.paid_amount)) : "cargando"} />
      <Stat label="Pendientes de la pyme" value={totals?.pending_client_count ?? "—"} note="documentos o antecedentes" />
      <Stat label="Saldo abierto" value={totals ? money.format(Number(totals.outstanding_amount)) : "—"} note={`${totals?.dispute_count ?? 0} en disputa`} />
    </section>
    {clientTrend && <article className="client-trend-card"><div className="card-heading"><div><p className="kicker">E10-05 · EVOLUCIÓN</p><h3>DSO y pago oportuno</h3></div><span className="read-only">Últimos 84 días</span></div><div className="trend-comparison"><div><span>DSO base</span><b>{clientTrend.baseline.dso ?? "—"} días</b><small>Actual: {clientTrend.outcomes.average_dso ?? "—"} días</small></div><div><span>Pago oportuno base</span><b>{clientTrend.baseline.on_time_percent ?? "—"}%</b><small>Actual: {clientTrend.outcomes.on_time_percent ?? "—"}%</small></div><div><span>Monto verificado</span><b>{money.format(Number(clientTrend.outcomes.verified_amount))}</b><small>{clientTrend.outcomes.settled_invoices} facturas saldadas</small></div></div><div className="mini-trend" aria-label="Tendencia semanal">{clientTrend.trend.map((point) => <div key={point.week_start} title={`${point.week_start}: ${point.on_time_percent ?? 0}% pago oportuno`}><span style={{ height: `${Math.max(Number(point.on_time_percent || 0), 4)}%` }} /><small>{point.week_start.slice(5)}</small></div>)}</div></article>}
    {userRole === "client" && escalations.length > 0 && <article className="client-escalations"><div className="card-heading"><div><p className="kicker">E10-04 · REQUIERE TU RESPUESTA</p><h3>Excepciones escaladas</h3></div><span className="read-only">{escalations.filter((item) => !item.response).length} pendientes</span></div><div className="client-escalation-list">{escalations.map((item) => <article key={item.id}><div><b>{item.invoice_folio || "Caso general"} · {item.payer_name || item.kind}</b><span>{item.note}</span><small>{new Date(item.escalated_at).toLocaleString("es-CL")}</small></div>{item.response ? <div className="client-response"><b>Respuesta registrada</b><span>{item.response.message}</span></div> : <><textarea aria-label={`Respuesta para ${item.invoice_folio || item.kind}`} placeholder="Información o decisión para el operador" value={escalationReplies[item.id] || ""} onChange={(event) => setEscalationReplies((current) => ({ ...current, [item.id]: event.target.value }))} /><div className="button-row"><button type="button" className="mini-button danger" disabled={responding === item.id} onClick={() => respondToEscalation(item, "rejected")}>No aprobar</button><button type="button" className="mini-button" disabled={responding === item.id} onClick={() => respondToEscalation(item, "information_provided")}>Responder</button><button type="button" className="mini-button" disabled={responding === item.id} onClick={() => respondToEscalation(item, "approved")}>Aprobar</button></div></>}</article>)}</div></article>}
    {userRole !== "client" && <article className="document-review-card"><div className="card-heading"><div><p className="kicker">E10-03 · REVISIÓN HUMANA</p><h3>Documentos pendientes</h3></div><span className="read-only">{submissions.length} por revisar</span></div><div className="document-review-list">{submissions.map((submission) => <article key={submission.id}><div><b>{submission.invoice_folio} · {submission.item_label}</b><span>{submission.original_name} · {submission.submitted_by_name}</span><small>SHA-256 {submission.content_sha256.slice(0, 16)}… · {new Date(submission.created_at).toLocaleString("es-CL")}</small></div><input aria-label={`Observación para ${submission.original_name}`} placeholder="Observación de revisión" value={reviewNotes[submission.id] || ""} onChange={(event) => setReviewNotes((current) => ({ ...current, [submission.id]: event.target.value }))} /><div className="button-row"><button type="button" className="mini-button danger" disabled={reviewing === submission.id} onClick={() => reviewDocument(submission, "rejected")}>Rechazar</button><button type="button" className="mini-button" disabled={reviewing === submission.id} onClick={() => reviewDocument(submission, "accepted")}>Aceptar</button></div></article>)}{!submissions.length && <p className="empty">No hay documentos pendientes para este cliente.</p>}</div></article>}
    <article className="table-card">
      <div className="card-heading"><div><p className="kicker">CARTERA AL {asOf}</p><h3>Estado y checklist</h3></div><span className="read-only">Vista sin acciones operativas</span></div>
      <div className="table-wrap"><table><thead><tr><th>Factura</th><th>Pagador</th><th>Vencimiento</th><th>Total</th><th>Pagado</th><th>Saldo</th><th>Pagabilidad</th><th>Pendiente pyme</th><th>Detalle</th></tr></thead><tbody>
        {(summary?.invoices || []).map((invoice) => <tr key={invoice.id}><td><b>{invoice.folio}</b><small>{statusLabels[invoice.status] || invoice.status}</small></td><td>{invoice.payer_name}</td><td>{invoice.due_on}</td><td className="number">{money.format(Number(invoice.total_amount))}</td><td className="number">{money.format(Number(invoice.paid_amount))}</td><td className="number">{money.format(Number(invoice.outstanding_amount))}</td><td><span className={`payability-pill ${invoice.payability_status}`}>{payabilityLabels[invoice.payability_status]} · {invoice.checklist_completed}/{invoice.checklist_total}</span></td><td>{invoice.pending_client_items.length ? <span className="missing">{invoice.pending_client_items.join(", ")}</span> : "Sin pendientes"}</td><td><div className="row-actions">{userRole === "client" && invoice.pending_client_items.length > 0 && <button type="button" className="mini-button" onClick={() => setDocumentTarget(invoice)}>Subir documento</button>}<button type="button" className="mini-button" onClick={() => onOpenChecklist(invoice)}>Ver checklist</button></div></td></tr>)}
        {!loading && !summary?.invoices?.length && <tr><td colSpan="9" className="empty">No hay facturas para la fecha seleccionada.</td></tr>}
        {loading && <tr><td colSpan="9" className="empty">Preparando resumen…</td></tr>}
      </tbody></table></div>
    </article>
    {documentTarget && <DocumentUploadDialog invoice={documentTarget} request={request} onClose={() => setDocumentTarget(null)} onUploaded={(submission) => { setDocumentTarget(null); setMessage({ type: "success", text: `${submission.original_name} quedó cifrado y pendiente de revisión.` }); load(); }} />}
  </section>;
}

function MetricsPanel({ clientId, request, download }) {
  const today = new Date().toISOString().slice(0, 10);
  const initialStart = new Date(); initialStart.setDate(initialStart.getDate() - 83);
  const [filters, setFilters] = useState({ date_from: initialStart.toISOString().slice(0, 10), date_to: today, human_hourly_cost_clp: "8000", usd_clp_rate: "950" });
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState(null);

  const params = useCallback(() => new URLSearchParams({ client_id: clientId, ...filters }).toString(), [clientId, filters]);
  const load = useCallback(async () => {
    if (!clientId) return;
    setLoading(true); setMessage(null);
    try { setReport(await request(`/api/v1/metrics/pilot?${params()}`)); }
    catch (error) { setMessage({ type: "error", text: error.message }); }
    finally { setLoading(false); }
  }, [clientId, params, request]);
  useEffect(() => { load(); }, [load]);

  function change(event) { setFilters((current) => ({ ...current, [event.target.name]: event.target.value })); }
  async function exportCsv() {
    try { await download(`/api/v1/metrics/pilot.csv?${params()}`, `metricas-piloto-${filters.date_to}.csv`); setMessage({ type: "success", text: "Métricas exportadas en CSV." }); }
    catch (error) { setMessage({ type: "error", text: error.message }); }
  }
  const percentage = (value) => value == null ? "—" : `${Number(value).toLocaleString("es-CL", { maximumFractionDigits: 1 })}%`;
  const decimal = (value, suffix = "") => value == null ? "—" : `${Number(value).toLocaleString("es-CL", { maximumFractionDigits: 1 })}${suffix}`;

  return <section className="metrics-layout">
    <Message value={message} onClose={() => setMessage(null)} />
    <article className="metrics-hero"><div><p className="kicker">FASE 7.3 · E11-02 A E11-07</p><h3>Métricas del piloto</h3><p>Resultados, operación y economía trazables desde pagos verificados, eventos y revisiones humanas.</p></div><div className="metrics-filters"><label>Desde<input type="date" name="date_from" value={filters.date_from} onChange={change} /></label><label>Hasta<input type="date" name="date_to" value={filters.date_to} onChange={change} /></label><label>Costo humano CLP/h<input type="number" min="0" name="human_hourly_cost_clp" value={filters.human_hourly_cost_clp} onChange={change} /></label><label>CLP por USD<input type="number" min="1" name="usd_clp_rate" value={filters.usd_clp_rate} onChange={change} /></label><button type="button" className="secondary" onClick={load} disabled={loading}>{loading ? "Calculando…" : "Calcular"}</button><button type="button" className="primary" onClick={exportCsv} disabled={!report}>Exportar CSV</button></div></article>
    {report && <>
      <section className="stats-grid"><Stat label="Facturas gestionadas" value={report.outcomes.managed_invoices} note={`${report.outcomes.settled_invoices} saldadas`} /><Stat label="Pago oportuno" value={percentage(report.outcomes.on_time_percent)} note={`base ${percentage(report.baseline.on_time_percent)}`} /><Stat label="DSO promedio" value={decimal(report.outcomes.average_dso, " días")} note={`base ${decimal(report.baseline.dso, " días")}`} /><Stat label="Monto recuperado" value={money.format(Number(report.outcomes.recovered_amount))} note="pagos posteriores al vencimiento" /><Stat label="Minutos humanos" value={decimal(report.operations.human_minutes)} note="excepciones + bitácora" /><Stat label="Costo por factura" value={report.economics.cost_per_managed_invoice_clp == null ? "—" : money.format(Number(report.economics.cost_per_managed_invoice_clp))} note="tecnología + operación" /><Stat label="Comisiones" value={money.format(Number(report.economics.commission_clp))} note="atribuciones verificadas" /><Stat label="Margen estimado" value={money.format(Number(report.economics.margin_clp))} note="con supuestos editables" /></section>
      <section className="metrics-grid">
        <article className="metric-card wide-card"><div className="card-heading"><div><p className="kicker">E11-03</p><h3>Tendencia semanal</h3></div><span className="read-only">{report.date_from} al {report.date_to}</span></div><div className="table-wrap"><table><thead><tr><th>Semana</th><th>Saldadas</th><th>Pago oportuno</th><th>DSO</th><th>Monto verificado</th></tr></thead><tbody>{report.trend.map((point) => <tr key={point.week_start}><td><b>{point.week_start}</b><small>al {point.week_end}</small></td><td>{point.settled_invoices}</td><td>{percentage(point.on_time_percent)}</td><td>{decimal(point.average_dso, " días")}</td><td className="number">{money.format(Number(point.verified_amount))}</td></tr>)}</tbody></table></div></article>
        <article className="metric-card"><div className="card-heading"><div><p className="kicker">E11-05</p><h3>Automatización</h3></div></div><div className="automation-list">{[["Mensajes", report.operations.messages], ["Clasificaciones", report.operations.classifications], ["Conciliaciones", report.operations.reconciliations]].map(([label, item]) => <div key={label}><span>{label}</span><b>{percentage(item.automatic_percent)}</b><small>{item.automatic} automáticas · {item.manual} manuales</small><progress max="100" value={Number(item.automatic_percent || 0)} /></div>)}</div></article>
        <article className="metric-card"><div className="card-heading"><div><p className="kicker">E11-02</p><h3>Economía del piloto</h3></div></div><dl className="metric-definition"><div><dt>Costo humano</dt><dd>{money.format(Number(report.economics.human_cost_clp))}</dd></div><div><dt>Costo tecnológico</dt><dd>{money.format(Number(report.economics.technology_cost_clp))}</dd></div><div><dt>Costo total</dt><dd>{money.format(Number(report.economics.total_cost_clp))}</dd></div><div><dt>LLM / mensajería</dt><dd>USD {Number(report.economics.llm_cost_usd).toFixed(4)} / {Number(report.economics.messaging_cost_usd).toFixed(4)}</dd></div></dl><p className="metric-note">{report.assumptions.note}</p></article>
        <article className="metric-card"><div className="card-heading"><div><p className="kicker">E11-06</p><h3>Causas de atraso</h3></div></div><div className="rank-list">{report.delay_causes.map((item) => <div key={item.category}><span>{item.category.replaceAll("_", " ")}</span><b>{item.invoice_count}</b><small>{money.format(Number(item.amount))}</small></div>)}{!report.delay_causes.length && <p className="empty">Sin causas registradas.</p>}</div></article>
        <article className="metric-card"><div className="card-heading"><div><p className="kicker">E11-07</p><h3>Resolución documental</h3></div></div><div className="rank-list">{report.resolution_times.map((item) => <div key={item.item_type}><span>{item.item_type.replaceAll("_", " ")}</span><b>{decimal(item.average_hours, " h")}</b><small>{item.resolved_count} requisitos resueltos</small></div>)}{!report.resolution_times.length && <p className="empty">Sin requisitos resueltos en el período.</p>}</div></article>
      </section>
    </>}
  </section>;
}

function FinalReportPanel({ request, download, user }) {
  const today = new Date().toISOString().slice(0, 10);
  const initialStart = new Date(); initialStart.setDate(initialStart.getDate() - 55);
  const [filters, setFilters] = useState({ date_from: initialStart.toISOString().slice(0, 10), date_to: today, human_hourly_cost_clp: "8000", usd_clp_rate: "950", minimum_group_size: "2", evidence_kind: "synthetic" });
  const [report, setReport] = useState(null);
  const [closures, setClosures] = useState([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState(null);
  const [decisionForms, setDecisionForms] = useState({});
  const params = useCallback(() => new URLSearchParams(filters).toString(), [filters]);
  const load = useCallback(async () => {
    setLoading(true); setMessage(null);
    try {
      const [reportResult, closureRows] = await Promise.all([
        request(`/api/v1/metrics/final-report?${params()}`),
        request("/api/v1/metrics/closures"),
      ]);
      setReport(reportResult); setClosures(closureRows);
    }
    catch (error) { setMessage({ type: "error", text: error.message }); }
    finally { setLoading(false); }
  }, [params, request]);
  useEffect(() => { load(); }, [load]);

  function change(event) { setFilters((current) => ({ ...current, [event.target.name]: event.target.value })); }
  async function exportArtifact(kind) {
    const isDataset = kind === "dataset";
    const endpoint = isDataset ? "anonymized-dataset.csv" : "final-report.md";
    const filename = isDataset ? `dataset-piloto-anonimizado-${filters.date_to}.csv` : `informe-final-v10-${filters.date_to}.md`;
    try {
      await download(`/api/v1/metrics/${endpoint}?${params()}`, filename);
      setMessage({ type: "success", text: isDataset ? "Dataset agregado y anonimizado exportado." : "Informe V-10 reproducible exportado." });
    } catch (error) { setMessage({ type: "error", text: error.message }); }
  }
  async function prepareClosure() {
    setSaving(true); setMessage(null);
    try {
      const snapshot = await request("/api/v1/metrics/closures", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ ...filters, human_hourly_cost_clp: Number(filters.human_hourly_cost_clp), usd_clp_rate: Number(filters.usd_clp_rate), minimum_group_size: Number(filters.minimum_group_size) }) });
      setClosures((current) => [snapshot, ...current.filter((item) => item.id !== snapshot.id)]);
      setMessage({ type: "success", text: "Snapshot inmutable preparado para revisión independiente." });
    } catch (error) { setMessage({ type: "error", text: error.message }); }
    finally { setSaving(false); }
  }
  async function decideClosure(snapshot) {
    const form = decisionForms[snapshot.id] || { decision: snapshot.recommendation === "pending" ? "iterate" : snapshot.recommendation, rationale: "" };
    if (form.rationale.trim().length < 20) { setMessage({ type: "error", text: "La justificación G4 debe tener al menos 20 caracteres." }); return; }
    setSaving(true); setMessage(null);
    try {
      const updated = await request(`/api/v1/metrics/closures/${snapshot.id}/decision`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(form) });
      setClosures((current) => current.map((item) => item.id === updated.id ? updated : item));
      setMessage({ type: "success", text: "Decisión G4 registrada con separación de funciones." });
    } catch (error) { setMessage({ type: "error", text: error.message }); }
    finally { setSaving(false); }
  }
  async function exportClosurePackage(snapshot) {
    try {
      await download(`/api/v1/metrics/closures/${snapshot.id}/package.zip`, `paquete-postulacion-${snapshot.report_fingerprint.slice(0, 16)}-${snapshot.status}.zip`);
      setMessage({ type: "success", text: snapshot.evidence_kind === "synthetic" ? "Paquete borrador generado con evidencia sintética y manifiesto verificable." : "Paquete de postulación generado desde el snapshot inmutable." });
    } catch (error) { setMessage({ type: "error", text: error.message }); }
  }
  function decisionForm(snapshot) { return decisionForms[snapshot.id] || { decision: snapshot.recommendation === "pending" ? "iterate" : snapshot.recommendation, rationale: "" }; }
  const percentage = (value) => value == null ? "—" : `${Number(value).toLocaleString("es-CL", { maximumFractionDigits: 1 })}%`;
  const decimal = (value, suffix = "") => value == null ? "—" : `${Number(value).toLocaleString("es-CL", { maximumFractionDigits: 1 })}${suffix}`;
  const hypothesisLabels = { confirmed: "Confirmada", rejected: "Rechazada", uncertain: "Incierta" };
  const resultLabels = { improved: "Mejora", declined: "Retroceso", mixed: "Mixto", insufficient_data: "Sin muestra" };
  const recommendationLabels = { pending: "Pendiente", scale: "Escalar", iterate: "Iterar", pivot: "Pivotar", stop: "Detener" };

  return <section className="final-report-layout">
    <Message value={message} onClose={() => setMessage(null)} />
    <article className="metrics-hero final-report-hero"><div><p className="kicker">FASE 8.1 · V-10</p><h3>Cierre verificable del piloto</h3><p>Compara cada pyme con su línea base, anonimiza el dataset y aplica la matriz G4 sin convertir una demostración sintética en evidencia real.</p></div><div className="metrics-filters final-report-filters"><label>Desde<input type="date" name="date_from" value={filters.date_from} onChange={change} /></label><label>Hasta<input type="date" name="date_to" value={filters.date_to} onChange={change} /></label><label>Costo humano CLP/h<input type="number" min="0" name="human_hourly_cost_clp" value={filters.human_hourly_cost_clp} onChange={change} /></label><label>CLP por USD<input type="number" min="1" name="usd_clp_rate" value={filters.usd_clp_rate} onChange={change} /></label><label>Mínimo por grupo<input type="number" min="1" max="50" name="minimum_group_size" value={filters.minimum_group_size} onChange={change} /></label><label>Tipo de evidencia<select name="evidence_kind" value={filters.evidence_kind} onChange={change}><option value="synthetic">Sintética / demo</option><option value="authorized_pilot">Piloto autorizado</option></select></label><button type="button" className="secondary" onClick={load} disabled={loading}>{loading ? "Calculando…" : "Recalcular"}</button></div></article>
    {report && <>
      <article className={`evidence-banner ${report.g4.ready ? "ready" : "pending"}`}><div><p className="kicker">PUERTA G4</p><h3>{recommendationLabels[report.g4.recommendation]}</h3><p>{report.g4.reason}</p></div><div><span>{report.evidence_kind === "synthetic" ? "Evidencia sintética" : "Piloto autorizado"}</span><b>{report.period_days} días · {report.portfolio.client_count} pymes</b><small>Autorizaciones {report.authorization_coverage.authorized_clients}/{report.authorization_coverage.participating_clients} · huella {report.fingerprint_sha256.slice(0, 16)}…</small></div></article>
      <section className="stats-grid"><Stat label="Pymes analizadas" value={report.portfolio.client_count} note="seudónimos estables" /><Stat label="Facturas gestionadas" value={report.portfolio.managed_invoices} note={`${report.portfolio.settled_invoices} saldadas`} /><Stat label="Pago oportuno" value={percentage(report.portfolio.on_time_percent)} note="ponderado por saldadas" /><Stat label="DSO agregado" value={decimal(report.portfolio.average_dso, " días")} note="ponderado por saldadas" /><Stat label="Monto verificado" value={money.format(Number(report.portfolio.verified_amount_clp))} note="solo pagos verificados" /><Stat label="Minutos humanos" value={decimal(report.portfolio.human_minutes)} note="operación + excepciones" /><Stat label="Costo total" value={money.format(Number(report.portfolio.total_cost_clp))} note="tecnología + personas" /><Stat label="Margen estimado" value={money.format(Number(report.portfolio.margin_clp))} note="supuestos reproducibles" /></section>
      <section className="report-actions"><div><b>Artefactos de cierre</b><span>El CSV excluye nombres, RUT, folios, contactos e IDs internos; grupos menores a {report.minimum_group_size} se suprimen.</span></div><button type="button" className="secondary" onClick={() => exportArtifact("dataset")}>Descargar dataset CSV</button><button type="button" className="secondary" onClick={() => exportArtifact("report")}>Descargar informe V-10</button><button type="button" className="primary" disabled={saving} onClick={prepareClosure}>Preparar snapshot</button></section>
      <section className="metrics-grid final-report-grid">
        <article className="metric-card wide-card"><div className="card-heading"><div><p className="kicker">COMPARACIÓN POR CLIENTE</p><h3>Línea base frente al piloto</h3></div><span className="read-only">Identidades anonimizadas</span></div><div className="table-wrap"><table><thead><tr><th>Pyme</th><th>DSO base</th><th>DSO actual</th><th>Δ días</th><th>Pago base</th><th>Pago actual</th><th>Δ puntos</th><th>Margen</th><th>Lectura</th></tr></thead><tbody>{report.client_comparisons.map((item) => <tr key={item.client_alias}><td><b>{item.client_alias}</b><small>{item.managed_invoices} gestionadas</small></td><td>{decimal(item.baseline_dso, " d")}</td><td>{decimal(item.current_dso, " d")}</td><td>{decimal(item.dso_delta_days, " d")}</td><td>{percentage(item.baseline_on_time_percent)}</td><td>{percentage(item.current_on_time_percent)}</td><td>{decimal(item.on_time_delta_points, " pp")}</td><td className="number">{money.format(Number(item.margin_clp))}</td><td><span className={`status-pill ${item.result}`}>{resultLabels[item.result]}</span></td></tr>)}</tbody></table></div></article>
        <article className="metric-card"><div className="card-heading"><div><p className="kicker">HIPÓTESIS</p><h3>Confirmadas, rechazadas e inciertas</h3></div></div><div className="hypothesis-list">{report.hypotheses.map((item) => <div key={item.key} className={item.state}><span>{hypothesisLabels[item.state]}</span><b>{item.statement}</b><small>{item.evidence}</small></div>)}</div></article>
        <article className="metric-card"><div className="card-heading"><div><p className="kicker">DECISIÓN</p><h3>Matriz G4</h3></div></div><div className="g4-matrix">{report.g4.matrix.map((item) => <div key={item.option} className={item.status}><span>{item.status === "recommended" ? "Recomendado" : item.status === "pending" ? "Pendiente" : "No recomendado"}</span><b>{item.label}</b></div>)}</div><div className="g4-checks">{report.g4.readiness_checks.map((item) => <span key={item.key} className={item.passed ? "passed" : "pending"}>{item.passed ? "✓" : "—"} {item.key.replaceAll("_", " ")}</span>)}</div></article>
        <article className="metric-card wide-card"><div className="card-heading"><div><p className="kicker">UNIT ECONOMICS</p><h3>Sensibilidad de margen</h3></div><span className="read-only">Supuestos explícitos</span></div><div className="table-wrap"><table><thead><tr><th>Escenario</th><th>Comisión</th><th>Costo humano</th><th>Tecnología</th><th>Costo / factura</th><th>Margen</th><th>Margen %</th></tr></thead><tbody>{report.economics_scenarios.map((item) => <tr key={item.key}><td><b>{item.label}</b><small>humano ×{item.human_minutes_factor} · tech ×{item.technology_cost_factor}</small></td><td className="number">{money.format(Number(item.commission_clp))}</td><td className="number">{money.format(Number(item.human_cost_clp))}</td><td className="number">{money.format(Number(item.technology_cost_clp))}</td><td className="number">{item.cost_per_managed_invoice_clp == null ? "—" : money.format(Number(item.cost_per_managed_invoice_clp))}</td><td className="number">{money.format(Number(item.margin_clp))}</td><td>{percentage(item.margin_percent)}</td></tr>)}</tbody></table></div></article>
        <article className="metric-card"><div className="card-heading"><div><p className="kicker">SIGUIENTE VERSIÓN</p><h3>Backlog por evidencia</h3></div></div><div className="backlog-priority-list">{report.backlog_priorities.map((item) => <div key={item.key}><i>{item.priority}</i><span><b>{item.action}</b><small>{item.rationale}</small></span></div>)}</div></article>
        {[["payer", "Pagador"], ["cause", "Causa"], ["amount_band", "Tramo de monto"]].map(([dimension, label]) => <article className="metric-card" key={dimension}><div className="card-heading"><div><p className="kicker">ANÁLISIS AGREGADO</p><h3>Por {label.toLowerCase()}</h3></div></div><div className="rank-list">{report.segments.filter((item) => item.dimension === dimension).map((item) => <div key={item.segment}><span>{item.segment.replaceAll("_", " ")}</span><b>{item.invoice_count}</b><small>{money.format(Number(item.nominal_amount_clp))} · {percentage(item.on_time_percent)} oportuno</small></div>)}{!report.segments.some((item) => item.dimension === dimension) && <p className="empty">Sin grupos que superen el umbral de privacidad.</p>}</div></article>)}
        <article className="metric-card"><div className="card-heading"><div><p className="kicker">PRIVACIDAD</p><h3>Control del dataset</h3></div></div><dl className="metric-definition"><div><dt>Método</dt><dd>{report.privacy.method}</dd></div><div><dt>Umbral k</dt><dd>{report.privacy.minimum_group_size}</dd></div><div><dt>Concentración mayor pagador</dt><dd>{percentage(report.payer_concentration_percent)}</dd></div><div><dt>Grupos suprimidos</dt><dd>{report.suppressed_groups.reduce((total, item) => total + item.groups, 0)}</dd></div></dl><p className="metric-note">Cohorte: {report.assumptions.cohort}</p></article>
      </section>
      <article className="closure-history"><div className="card-heading"><div><p className="kicker">CONTROL DE CAMBIOS</p><h3>Snapshots y decisiones G4</h3></div><span className="read-only">Preparación y aprobación separadas</span></div><div className="closure-list">{closures.map((snapshot) => { const form = decisionForm(snapshot); const canDecide = user.role === "admin" && snapshot.status === "prepared" && snapshot.report_data?.g4?.ready && snapshot.prepared_by !== user.id; return <article key={snapshot.id}><div className="closure-meta"><span className={`status-pill ${snapshot.status}`}>{snapshot.status === "decided" ? "Decidido" : "Preparado"}</span><b>{snapshot.date_from} al {snapshot.date_to}</b><small>{snapshot.evidence_kind} · {snapshot.report_fingerprint.slice(0, 16)}…</small></div><div><span>Recomendación</span><b>{recommendationLabels[snapshot.recommendation]}</b>{snapshot.decision && <small>Decisión: {recommendationLabels[snapshot.decision]} · {snapshot.decision_rationale}</small>}</div><div className="closure-package-actions"><button type="button" className="secondary" onClick={() => exportClosurePackage(snapshot)}>Descargar paquete ZIP</button>{canDecide ? <div className="closure-decision"><select value={form.decision} onChange={(event) => setDecisionForms((current) => ({ ...current, [snapshot.id]: { ...form, decision: event.target.value } }))}><option value="scale">Escalar</option><option value="iterate">Iterar</option><option value="pivot">Pivotar</option><option value="stop">Detener</option></select><textarea placeholder="Justificación de la decisión (mínimo 20 caracteres)" value={form.rationale} onChange={(event) => setDecisionForms((current) => ({ ...current, [snapshot.id]: { ...form, rationale: event.target.value } }))} /><button type="button" className="primary" disabled={saving} onClick={() => decideClosure(snapshot)}>Registrar decisión</button></div> : <p className="closure-note">{snapshot.status === "decided" ? "Snapshot cerrado e inmutable." : !snapshot.report_data?.g4?.ready ? "La evidencia no habilita una decisión G4." : snapshot.prepared_by === user.id ? "Debe decidir otro administrador." : "Solo un administrador puede decidir."}</p>}</div></article>; })}{!closures.length && <p className="empty">Aún no hay snapshots preparados.</p>}</div></article>
    </>}
  </section>;
}

function PilotOperationsPanel({ clientId, invoices, request, onOpenView }) {
  const today = new Date().toISOString().slice(0, 10);
  const [operationDate, setOperationDate] = useState(() => typeof window === "undefined" ? today : (localStorage.getItem("recupera_demo_date") || today));
  const [walkthrough, setWalkthrough] = useState(null);
  const [entries, setEntries] = useState([]);
  const [message, setMessage] = useState(null);
  const [busy, setBusy] = useState(false);
  const [resolutionNotes, setResolutionNotes] = useState({});
  const [form, setForm] = useState({ entry_type: "incident", severity: "warning", title: "", detail: "", occurred_on: today, human_minutes: "0", related_invoice_id: "" });

  const load = useCallback(async () => {
    if (!clientId) return;
    try {
      const [logRows, walkthroughResult] = await Promise.all([
        request(`/api/v1/pilot/log?client_id=${clientId}`),
        request(`/api/v1/pilot/demo-walkthrough?client_id=${clientId}&operation_date=${operationDate}`),
      ]);
      setEntries(logRows); setWalkthrough(walkthroughResult);
    } catch (error) { setMessage({ type: "error", text: error.message }); }
  }, [clientId, operationDate, request]);
  useEffect(() => { load(); }, [load]);

  function fixOperationDate(value) {
    setOperationDate(value);
    localStorage.setItem("recupera_demo_date", value);
  }
  async function createEntry(event) {
    event.preventDefault(); setBusy(true); setMessage(null);
    try {
      await request("/api/v1/pilot/log", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ ...form, client_id: clientId, human_minutes: Number(form.human_minutes), related_invoice_id: form.related_invoice_id || null }) });
      setForm((current) => ({ ...current, title: "", detail: "", human_minutes: "0", related_invoice_id: "" }));
      setMessage({ type: "success", text: "Registro incorporado a la bitácora auditable." });
      await load();
    } catch (error) { setMessage({ type: "error", text: error.message }); }
    finally { setBusy(false); }
  }
  async function resolveEntry(entry) {
    const note = (resolutionNotes[entry.id] || "").trim();
    if (note.length < 3) { setMessage({ type: "error", text: "Describe cómo se resolvió la incidencia." }); return; }
    setBusy(true); setMessage(null);
    try {
      await request(`/api/v1/pilot/log/${entry.id}/resolve`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ client_id: clientId, resolution_note: note }) });
      setMessage({ type: "success", text: "Incidencia resuelta con trazabilidad." });
      await load();
    } catch (error) { setMessage({ type: "error", text: error.message }); }
    finally { setBusy(false); }
  }
  const typeLabels = { decision: "Decisión", incident: "Incidencia", manual_work: "Trabajo manual", rule_change: "Cambio de regla", learning: "Aprendizaje" };

  return <section className="pilot-operations-layout">
    <Message value={message} onClose={() => setMessage(null)} />
    <article className="demo-walkthrough"><div className="card-heading"><div><p className="kicker">E0-08 · RECORRIDO CONTROLADO</p><h3>Demostración de punta a punta</h3></div><label>Fecha de operación<input type="date" value={operationDate} onChange={(event) => fixOperationDate(event.target.value)} /></label></div>{walkthrough && <><div className="walkthrough-progress"><b>{walkthrough.ready_steps}/{walkthrough.total_steps} etapas con evidencia</b><progress max={walkthrough.total_steps} value={walkthrough.ready_steps} /></div><div className="walkthrough-steps">{walkthrough.steps.map((step, index) => <button type="button" key={step.key} className={step.ready ? "ready" : "pending"} onClick={() => onOpenView(step.target_view)}><i>{index + 1}</i><span><b>{step.label}</b><small>{step.ready ? "Evidencia disponible" : "Pendiente para esta fecha"}</small></span><em>{step.ready ? "✓" : "—"}</em></button>)}</div><p className="metric-note">La fecha controla este recorrido de lectura; no altera la base ni dispara comunicaciones externas.</p></>}</article>
    <article className="pilot-log-form-card"><div className="card-heading"><div><p className="kicker">OPERACIÓN Y APRENDIZAJE</p><h3>Registrar actividad del piloto</h3></div></div><form className="pilot-log-form" onSubmit={createEntry}><label>Tipo<select value={form.entry_type} onChange={(event) => setForm((current) => ({ ...current, entry_type: event.target.value }))}>{Object.entries(typeLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label><label>Severidad<select value={form.severity} onChange={(event) => setForm((current) => ({ ...current, severity: event.target.value }))}><option value="info">Informativa</option><option value="warning">Advertencia</option><option value="critical">Crítica</option></select></label><label>Fecha<input type="date" required value={form.occurred_on} onChange={(event) => setForm((current) => ({ ...current, occurred_on: event.target.value }))} /></label><label>Minutos humanos<input type="number" min="0" max="1440" step="0.1" value={form.human_minutes} onChange={(event) => setForm((current) => ({ ...current, human_minutes: event.target.value }))} /></label><label className="wide">Factura relacionada<select value={form.related_invoice_id} onChange={(event) => setForm((current) => ({ ...current, related_invoice_id: event.target.value }))}><option value="">Caso general</option>{invoices.map((invoice) => <option key={invoice.id} value={invoice.id}>{invoice.folio} · {invoice.payer_name}</option>)}</select></label><label className="wide">Título<input required minLength="3" maxLength="200" value={form.title} onChange={(event) => setForm((current) => ({ ...current, title: event.target.value }))} /></label><label className="wide">Detalle<textarea required minLength="3" maxLength="4000" value={form.detail} onChange={(event) => setForm((current) => ({ ...current, detail: event.target.value }))} /></label><button className="primary" disabled={busy}>Guardar registro</button></form></article>
    <article className="pilot-log-card"><div className="card-heading"><div><p className="kicker">TRAZABILIDAD</p><h3>Decisiones e incidencias</h3></div><span className="read-only">{entries.filter((entry) => entry.status === "open").length} abiertas</span></div><div className="pilot-log-list">{entries.map((entry) => <article key={entry.id} className={`${entry.severity} ${entry.status}`}><div className="pilot-log-meta"><span>{typeLabels[entry.entry_type] || entry.entry_type}</span><small>{entry.occurred_on} · {entry.human_minutes} min</small></div><div><b>{entry.title}</b><p>{entry.detail}</p>{entry.resolution_note && <small>Resolución: {entry.resolution_note}</small>}</div><span className={`status-pill ${entry.status}`}>{entry.status}</span>{entry.status === "open" && <div className="pilot-resolve"><input placeholder="Resolución aplicada" value={resolutionNotes[entry.id] || ""} onChange={(event) => setResolutionNotes((current) => ({ ...current, [entry.id]: event.target.value }))} /><button type="button" className="mini-button" disabled={busy} onClick={() => resolveEntry(entry)}>Resolver</button></div>}</article>)}{!entries.length && <p className="empty">Aún no hay registros para este cliente.</p>}</div></article>
  </section>;
}

function ContractPanel({ clientId, request }) {
  const [contracts, setContracts] = useState([]);
  const [jobs, setJobs] = useState([]);
  const [readiness, setReadiness] = useState(null);
  const [authorizationEvidence, setAuthorizationEvidence] = useState(null);
  const [authorizationForm, setAuthorizationForm] = useState({ name: "", email: "", valid_from: new Date().toISOString().slice(0, 10), valid_until: "", note: "" });
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState(null);
  const [simulationDate, setSimulationDate] = useState(new Date().toISOString().slice(0, 10));
  const [simulation, setSimulation] = useState([]);
  const [form, setForm] = useState({
    window_start: "09:00",
    window_end: "18:00",
    max_contacts_per_week: 2,
    tone: "cordial",
    preventive_days_before_due: 7,
    escalation_days_after_due: 15,
    preventive_percent: 0,
    recovery_percent: 0,
    email: true,
    whatsapp_assisted: false,
  });

  const loadContracts = useCallback(async () => {
    if (!clientId) return;
    try {
      setContracts(await request(`/api/v1/contracts?client_id=${clientId}`));
    } catch (error) {
      setMessage({ type: "error", text: error.message });
    }
  }, [clientId, request]);

  const loadJobs = useCallback(async () => {
    if (!clientId) return;
    try {
      setJobs(await request(`/api/v1/workflows/jobs?client_id=${clientId}&limit=30`));
    } catch (error) {
      setMessage({ type: "error", text: error.message });
    }
  }, [clientId, request]);

  const loadReadiness = useCallback(async () => {
    if (!clientId) return;
    try { setReadiness(await request(`/api/v1/pilot/readiness?client_id=${clientId}`)); }
    catch (error) { setMessage({ type: "error", text: error.message }); }
  }, [clientId, request]);

  useEffect(() => { loadContracts(); loadJobs(); loadReadiness(); }, [loadContracts, loadJobs, loadReadiness]);

  function change(event) {
    const value = event.target.type === "checkbox" ? event.target.checked : event.target.value;
    setForm((current) => ({ ...current, [event.target.name]: value }));
  }

  async function save(event) {
    event.preventDefault();
    setBusy(true);
    setMessage(null);
    try {
      const channels = [form.email && "email", form.whatsapp_assisted && "whatsapp_assisted"].filter(Boolean);
      await request("/api/v1/contracts", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          client_id: clientId,
          activate: true,
          rules: {
            timezone: "America/Santiago",
            allowed_weekdays: [0, 1, 2, 3, 4],
            window_start: form.window_start,
            window_end: form.window_end,
            max_contacts_per_week: Number(form.max_contacts_per_week),
            channels,
            tone: form.tone,
            preventive_days_before_due: Number(form.preventive_days_before_due),
            escalation_days_after_due: Number(form.escalation_days_after_due),
            commission: {
              preventive_percent: Number(form.preventive_percent),
              recovery_percent: Number(form.recovery_percent),
            },
          },
        }),
      });
      setMessage({ type: "success", text: "Se creó y activó una nueva versión del contrato." });
      await loadContracts(); await loadReadiness();
    } catch (error) {
      setMessage({ type: "error", text: error.message });
    } finally {
      setBusy(false);
    }
  }

  async function runCycle() {
    setBusy(true);
    setMessage(null);
    try {
      const result = await request("/api/v1/workflows/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ client_id: clientId, mode: "manual" }),
      });
      setMessage({
        type: "success",
        text: `Ciclo listo: ${result.invoices_evaluated} facturas evaluadas, ${result.jobs_created} trabajos creados y ${result.jobs_skipped} omitidos.`,
      });
      await loadJobs();
    } catch (error) {
      setMessage({ type: "error", text: error.message });
    } finally {
      setBusy(false);
    }
  }

  async function runSimulation() {
    setBusy(true);
    setMessage(null);
    try {
      const result = await request("/api/v1/workflows/simulate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ client_id: clientId, simulation_date: simulationDate }),
      });
      setSimulation(result);
      setMessage({ type: "success", text: `Simulación lista para ${result.length} facturas. No se modificaron estados ni trabajos.` });
    } catch (error) {
      setMessage({ type: "error", text: error.message });
    } finally {
      setBusy(false);
    }
  }

  async function approvePilot(event) {
    event.preventDefault();
    const currentContract = contracts.find((contract) => contract.active);
    if (!currentContract || !authorizationEvidence) { setMessage({ type: "error", text: "Se requiere contrato activo y evidencia firmada." }); return; }
    setBusy(true); setMessage(null);
    const data = new FormData();
    data.append("client_id", clientId); data.append("contract_id", currentContract.id); data.append("channels_json", JSON.stringify(currentContract.rules.channels)); data.append("authorized_contact_name", authorizationForm.name); data.append("authorized_contact_email", authorizationForm.email); data.append("valid_from", authorizationForm.valid_from); if (authorizationForm.valid_until) data.append("valid_until", authorizationForm.valid_until); if (authorizationForm.note) data.append("note", authorizationForm.note); data.append("evidence", authorizationEvidence);
    try { await request("/api/v1/pilot/authorizations", { method: "POST", body: data }); setMessage({ type: "success", text: "Autorización registrada con evidencia cifrada." }); setAuthorizationEvidence(null); await loadReadiness(); }
    catch (error) { setMessage({ type: "error", text: error.message }); }
    finally { setBusy(false); }
  }

  async function revokePilot() {
    if (!readiness?.authorization?.id) return;
    setBusy(true); setMessage(null);
    try { await request(`/api/v1/pilot/authorizations/${readiness.authorization.id}/revoke`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ client_id: clientId, note: "Revocación registrada desde la consola operativa." }) }); setMessage({ type: "success", text: "Autorización revocada; la puerta del piloto quedó cerrada." }); await loadReadiness(); }
    catch (error) { setMessage({ type: "error", text: error.message }); }
    finally { setBusy(false); }
  }

  const active = contracts.find((contract) => contract.active);
  return (
    <section className="contract-layout">
      <article className="contract-card">
        <div className="card-heading">
          <div><p className="kicker">E2-01 A E2-05</p><h3>Reglas de operación</h3></div>
          {active && <span className="active-version">Versión {active.version} activa</span>}
        </div>
        <form className="contract-form" onSubmit={save}>
          <div className="form-section">
            <h4>Horario y frecuencia</h4>
            <div className="form-grid">
              <label>Desde<input type="time" name="window_start" value={form.window_start} onChange={change} required /></label>
              <label>Hasta<input type="time" name="window_end" value={form.window_end} onChange={change} required /></label>
              <label>Contactos máximos por semana<input type="number" name="max_contacts_per_week" min="1" max="7" value={form.max_contacts_per_week} onChange={change} required /></label>
              <label>Tono<select name="tone" value={form.tone} onChange={change}><option value="cordial">Cordial</option><option value="direct">Directo</option><option value="formal">Formal</option></select></label>
            </div>
            <p className="form-hint">Lunes a viernes · Zona horaria America/Santiago</p>
          </div>
          <div className="form-section">
            <h4>Etapas y canales</h4>
            <div className="form-grid">
              <label>Días de prevención<input type="number" name="preventive_days_before_due" min="1" max="30" value={form.preventive_days_before_due} onChange={change} required /></label>
              <label>Días hasta escalamiento<input type="number" name="escalation_days_after_due" min="1" max="90" value={form.escalation_days_after_due} onChange={change} required /></label>
            </div>
            <div className="check-row">
              <label><input type="checkbox" name="email" checked={form.email} onChange={change} /> Email</label>
              <label><input type="checkbox" name="whatsapp_assisted" checked={form.whatsapp_assisted} onChange={change} /> WhatsApp asistido</label>
            </div>
          </div>
          <div className="form-section">
            <h4>Comisión</h4>
            <div className="form-grid">
              <label>Preventiva (%)<input type="number" name="preventive_percent" min="0" max="100" step="0.1" value={form.preventive_percent} onChange={change} /></label>
              <label>Recuperación (%)<input type="number" name="recovery_percent" min="0" max="100" step="0.1" value={form.recovery_percent} onChange={change} /></label>
            </div>
          </div>
          <div className="button-row end">
            <button type="button" className="secondary" disabled={!active || busy} onClick={runCycle}>Ejecutar ciclo manual</button>
            <button className="primary" disabled={busy || (!form.email && !form.whatsapp_assisted)}>{busy ? "Procesando…" : "Guardar nueva versión"}</button>
          </div>
        </form>
        <div className="jobs-panel">
          <div className="jobs-heading"><div><p className="kicker">E4-04 / E4-08</p><h4>Trabajos recientes</h4></div><button type="button" className="ghost" onClick={loadJobs}>Actualizar</button></div>
          <div className="table-wrap">
            <table>
              <thead><tr><th>Programado</th><th>Etapa</th><th>Facturas agrupadas</th><th>Estado</th><th>Modo</th></tr></thead>
              <tbody>
                {jobs.map((job) => (
                  <tr key={job.id}>
                    <td>{new Date(job.scheduled_for).toLocaleString("es-CL")}</td>
                    <td><b className="stage-label">{job.stage}</b><small>{job.action_type}</small></td>
                    <td>{job.payload?.invoice_ids?.length ?? 1}</td>
                    <td><span className={`job-status ${job.status}`}>{job.status}</span></td>
                    <td>{job.mode}</td>
                  </tr>
                ))}
                {!jobs.length && <tr><td colSpan="5" className="empty">Ejecuta un ciclo para generar trabajos.</td></tr>}
              </tbody>
            </table>
          </div>
        </div>
        <div className="simulation-panel">
          <div className="jobs-heading"><div><p className="kicker">SIMULACIÓN SEGURA</p><h4>Evaluar una fecha sin modificar datos</h4></div><div className="simulation-actions"><input type="date" value={simulationDate} onChange={(event) => setSimulationDate(event.target.value)} /><button type="button" className="secondary" disabled={!active || busy} onClick={runSimulation}>Simular</button></div></div>
          {simulation.length > 0 && <div className="table-wrap"><table><thead><tr><th>Factura</th><th>Pagador</th><th>Etapa</th><th>Decisión</th><th>Próxima ventana</th></tr></thead><tbody>{simulation.map((item) => <tr key={item.invoice_id}><td><b>{item.folio}</b><small>Contrato v{item.contract_version}</small></td><td>{item.payer_name}</td><td><b className="stage-label">{stageLabels[item.stage] ?? item.stage}</b></td><td>{item.state_status}<small>{item.pause_reason ?? item.action_type ?? "Sin acción"}</small></td><td>{item.scheduled_for ? new Date(item.scheduled_for).toLocaleString("es-CL") : "—"}</td></tr>)}</tbody></table></div>}
        </div>
      </article>
      <aside className="version-card">
        <p className="kicker">TRAZABILIDAD</p>
        <h3>Versiones</h3>
        <p className="muted">Cada ejecución conserva el contrato y la versión que determinaron sus reglas.</p>
        <div className="version-list">
          {contracts.map((contract) => (
            <div key={contract.id} className={contract.active ? "active" : ""}>
              <b>Versión {contract.version}</b><span>{contract.active ? "Activa" : "Histórica"}</span><small>{new Date(contract.created_at).toLocaleString("es-CL")}</small>
            </div>
          ))}
          {!contracts.length && <p className="empty-version">Aún no hay contrato configurado.</p>}
        </div>
        <div className={`pilot-readiness ${readiness?.ready ? "ready" : "blocked"}`}>
          <p className="kicker">PUERTA G3</p>
          <h3>{readiness?.ready ? "Cliente preparado" : "Preparación pendiente"}</h3>
          <div className="readiness-checks">{Object.entries(readiness?.checks || {}).map(([key, passed]) => <span key={key} className={passed ? "passed" : "failed"}><i>{passed ? "✓" : "!"}</i>{key.replaceAll("_", " ")}</span>)}</div>
          {readiness?.blockers?.map((blocker) => <small key={blocker}>{blocker}</small>)}
          {readiness?.authorization?.action === "approved" && <button type="button" className="mini-button danger" disabled={busy} onClick={revokePilot}>Revocar autorización</button>}
        </div>
        {active && readiness?.authorization?.action !== "approved" && <form className="pilot-authorization-form" onSubmit={approvePilot}>
          <p className="kicker">AUTORIZACIÓN OPERATIVA</p><h3>Registrar mandato</h3>
          <label>Representante<input required minLength="2" value={authorizationForm.name} onChange={(event) => setAuthorizationForm((current) => ({ ...current, name: event.target.value }))} /></label>
          <label>Correo<input required type="email" value={authorizationForm.email} onChange={(event) => setAuthorizationForm((current) => ({ ...current, email: event.target.value }))} /></label>
          <label>Vigente desde<input required type="date" value={authorizationForm.valid_from} onChange={(event) => setAuthorizationForm((current) => ({ ...current, valid_from: event.target.value }))} /></label>
          <label>Vigente hasta<input type="date" value={authorizationForm.valid_until} onChange={(event) => setAuthorizationForm((current) => ({ ...current, valid_until: event.target.value }))} /></label>
          <label>Evidencia firmada<input required type="file" onChange={(event) => setAuthorizationEvidence(event.target.files?.[0] || null)} /></label>
          <label>Nota<textarea rows="3" value={authorizationForm.note} onChange={(event) => setAuthorizationForm((current) => ({ ...current, note: event.target.value }))} /></label>
          <button className="secondary" disabled={busy || !authorizationEvidence}>Registrar autorización</button>
          <p className="form-help">No crea una autorización legal: registra de forma auditable la evidencia ya firmada.</p>
        </form>}
        <Message value={message} onClose={() => setMessage(null)} />
      </aside>
    </section>
  );
}

export default function Home() {
  const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
  const [apiState, setApiState] = useState("checking");
  const [token, setToken] = useState("");
  const [user, setUser] = useState(null);
  const [clients, setClients] = useState([]);
  const [selectedClientId, setSelectedClientId] = useState("");
  const [invoices, setInvoices] = useState([]);
  const [workflowStates, setWorkflowStates] = useState([]);
  const [workflowControls, setWorkflowControls] = useState([]);
  const [loadingInvoices, setLoadingInvoices] = useState(false);
  const [message, setMessage] = useState(null);
  const [showClientForm, setShowClientForm] = useState(false);
  const [pauseTarget, setPauseTarget] = useState(null);
  const [timeline, setTimeline] = useState(null);
  const [timelineEvents, setTimelineEvents] = useState([]);
  const [timelineLoading, setTimelineLoading] = useState(false);
  const [payabilityChecklist, setPayabilityChecklist] = useState(null);
  const [activeView, setActiveView] = useState("portfolio");

  useEffect(() => {
    fetch(`${apiUrl}/health/ready`).then((response) => setApiState(response.ok ? "ready" : "offline")).catch(() => setApiState("offline"));
  }, [apiUrl]);

  const request = useCallback(async (path, options = {}, overrideToken = token) => {
    const headers = new Headers(options.headers ?? {});
    if (overrideToken) headers.set("Authorization", `Bearer ${overrideToken}`);
    const response = await fetch(`${apiUrl}${path}`, { ...options, headers });
    const payload = response.status === 204 ? null : await response.json();
    if (!response.ok) {
      const detail = Array.isArray(payload?.detail) ? payload.detail.map((item) => item.msg).join(" · ") : payload?.detail;
      throw new Error(detail ?? `Error ${response.status}`);
    }
    return payload;
  }, [apiUrl, token]);

  const download = useCallback(async (path, filename) => {
    const response = await fetch(`${apiUrl}${path}`, { headers: { Authorization: `Bearer ${token}` } });
    if (!response.ok) {
      let detail = `Error ${response.status}`;
      try { detail = (await response.json()).detail || detail; } catch { /* respuesta no JSON */ }
      throw new Error(detail);
    }
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url; anchor.download = filename; anchor.click();
    URL.revokeObjectURL(url);
  }, [apiUrl, token]);

  const startSession = useCallback(async (accessToken) => {
    try {
      const profile = await request("/api/v1/auth/me", {}, accessToken);
      setToken(accessToken);
      setUser(profile);
      sessionStorage.setItem("recupera_token", accessToken);
      if (profile.role === "client") {
        setActiveView("client_portal");
        setSelectedClientId(profile.client_id);
      } else {
        const availableClients = await request("/api/v1/clients", {}, accessToken);
        setClients(availableClients);
        setSelectedClientId((current) => current || availableClients[0]?.id || "");
      }
    } catch (error) {
      sessionStorage.removeItem("recupera_token");
      setToken("");
      setUser(null);
      setMessage({ type: "error", text: error.message });
    }
  }, [request]);

  useEffect(() => {
    const stored = sessionStorage.getItem("recupera_token");
    if (stored) startSession(stored);
  }, [startSession]);

  const loadInvoices = useCallback(async () => {
    if (!token || !selectedClientId) return;
    setLoadingInvoices(true);
    try {
      const query = user?.role === "client" ? "" : `?client_id=${selectedClientId}`;
      const stateQuery = user?.role === "client" ? "" : `?client_id=${selectedClientId}`;
      const requests = [
        request(`/api/v1/invoices${query}`),
        request(`/api/v1/workflows/states${stateQuery}`),
      ];
      if (user?.role === "admin" || user?.role === "operator") {
        requests.push(request(`/api/v1/workflows/controls?client_id=${selectedClientId}`));
      }
      const [invoiceRows, stateRows, controlRows = []] = await Promise.all(requests);
      setInvoices(invoiceRows);
      setWorkflowStates(stateRows);
      setWorkflowControls(controlRows);
    } catch (error) {
      setMessage({ type: "error", text: error.message });
    } finally {
      setLoadingInvoices(false);
    }
  }, [request, selectedClientId, token, user?.role]);

  useEffect(() => { loadInvoices(); }, [loadInvoices]);

  function logout() {
    sessionStorage.removeItem("recupera_token");
    setToken("");
    setUser(null);
    setClients([]);
    setInvoices([]);
    setWorkflowStates([]);
    setWorkflowControls([]);
    setActiveView("portfolio");
  }

  async function updateStatus(invoiceId, status) {
    try {
      await request(`/api/v1/invoices/${invoiceId}/status`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ client_id: selectedClientId, status }),
      });
      setMessage({ type: "success", text: `Estado actualizado a ${statusLabels[status].toLowerCase()}.` });
      loadInvoices();
    } catch (error) {
      setMessage({ type: "error", text: error.message });
    }
  }

  async function changeWorkflowControl(target, action, reason = null, resumeAt = "") {
    try {
      await request("/api/v1/workflows/controls", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          client_id: selectedClientId,
          scope_type: target.scopeType,
          scope_id: target.scopeId,
          action,
          reason,
          resume_at: resumeAt ? new Date(resumeAt).toISOString() : null,
        }),
      });
      await request("/api/v1/workflows/run", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ client_id: selectedClientId, mode: "manual" }),
      });
      setMessage({ type: "success", text: action === "resume" ? `${target.label} reanudado.` : `${target.label} pausado.` });
      setPauseTarget(null);
      await loadInvoices();
    } catch (error) {
      setMessage({ type: "error", text: error.message });
    }
  }

  async function showTimeline(invoice) {
    setTimeline(invoice);
    setTimelineEvents([]);
    setTimelineLoading(true);
    try {
      const query = user?.role === "client" ? "" : `?client_id=${selectedClientId}`;
      setTimelineEvents(await request(`/api/v1/invoices/${invoice.id}/events${query}`));
    } catch (error) {
      setMessage({ type: "error", text: error.message });
    } finally {
      setTimelineLoading(false);
    }
  }

  async function loadPayability(invoice) {
    try {
      const query = user?.role === "client" ? "" : `?client_id=${selectedClientId}`;
      setPayabilityChecklist(await request(`/api/v1/payability/invoices/${invoice.id}${query}`));
    } catch (error) {
      setMessage({ type: "error", text: error.message });
    }
  }

  async function refreshPayability() {
    if (!payabilityChecklist) return;
    const query = user?.role === "client" ? "" : `?client_id=${selectedClientId}`;
    setPayabilityChecklist(await request(`/api/v1/payability/invoices/${payabilityChecklist.invoice_id}${query}`));
    await loadInvoices();
  }

  const metrics = useMemo(() => {
    const total = invoices.reduce((sum, invoice) => sum + Number(invoice.total_amount), 0);
    const due = invoices.filter((invoice) => new Date(`${invoice.due_on}T00:00:00`) < new Date() && invoice.status === "issued");
    return {
      total,
      dueCount: due.length,
      dueAmount: due.reduce((sum, invoice) => sum + Number(invoice.total_amount), 0),
      paidCount: invoices.filter((invoice) => invoice.status === "paid").length,
      payableCount: invoices.filter((invoice) => invoice.payability_status === "payable").length,
      riskCount: invoices.filter((invoice) => invoice.payability_status === "at_risk" || invoice.payability_status === "claimed").length,
    };
  }, [invoices]);

  const selectedClient = clients.find((client) => client.id === selectedClientId);
  const workflowStateByInvoice = new Map(workflowStates.map((state) => [state.invoice_id, state]));
  const controlByScope = new Map(workflowControls.map((control) => [`${control.scope_type}:${control.scope_id}`, control]));
  const payerGroups = useMemo(() => {
    const groups = new Map();
    for (const invoice of invoices) {
      const current = groups.get(invoice.payer_id) ?? { payerId: invoice.payer_id, payerName: invoice.payer_name, invoices: 0, amount: 0 };
      current.invoices += 1;
      current.amount += Number(invoice.total_amount);
      groups.set(invoice.payer_id, current);
    }
    return [...groups.values()].sort((a, b) => a.payerName.localeCompare(b.payerName));
  }, [invoices]);
  const canOperate = user?.role === "admin" || user?.role === "operator";
  const viewTitle = {
    client_portal: ["RESUMEN PARA LA PYME", "Vista cliente y reporte semanal"],
    portfolio: ["OPERACIÓN", "Cartera de facturas"],
    imports: ["CARGA DE DATOS", "Importaciones"],
    contract: ["REGLAS Y TRAZABILIDAD", "Contrato y motor operativo"],
    payability: ["PAGABILIDAD", "Ficha del pagador y requisitos"],
    communications: ["COMUNICACIONES", "Bandeja multicanal simulada"],
    exceptions: ["IA SUPERVISADA", "Clasificación y excepciones"],
    payments: ["PAGOS", "Conciliación supervisada"],
    access: ["SEGURIDAD", "Registro de accesos"],
    metrics: ["PILOTO", "Métricas operativas y económicas"],
    pilot_operations: ["PILOTO ASISTIDO", "Recorrido, decisiones e incidencias"],
    final_report: ["FASE 8", "Informe final y decisión G4"],
  }[activeView];

  if (!user) return <Login apiUrl={apiUrl} apiState={apiState} onAuthenticated={startSession} />;

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <div className="brand brand-light"><span>R</span> Recupera</div>
        <nav className="side-nav" aria-label="Navegación principal">
          <button className={activeView === "client_portal" ? "active" : ""} onClick={() => setActiveView("client_portal")}><i>{canOperate ? "09" : "01"}</i>{canOperate ? "Vista cliente" : "Mi resumen"}</button>
          <button className={activeView === "portfolio" ? "active" : ""} onClick={() => setActiveView("portfolio")}><i>{canOperate ? "01" : "02"}</i>Cartera</button>
          {canOperate && <button className={activeView === "imports" ? "active" : ""} onClick={() => setActiveView("imports")}><i>02</i>Importaciones</button>}
          {canOperate && <button className={activeView === "contract" ? "active" : ""} onClick={() => setActiveView("contract")}><i>03</i>Contrato y flujo</button>}
          {canOperate && <button className={activeView === "payability" ? "active" : ""} onClick={() => setActiveView("payability")}><i>04</i>Pagabilidad</button>}
          {canOperate && <button className={activeView === "communications" ? "active" : ""} onClick={() => setActiveView("communications")}><i>05</i>Comunicaciones</button>}
          {canOperate && <button className={activeView === "exceptions" ? "active" : ""} onClick={() => setActiveView("exceptions")}><i>06</i>Excepciones</button>}
          {canOperate && <button className={activeView === "payments" ? "active" : ""} onClick={() => setActiveView("payments")}><i>07</i>Pagos</button>}
          {user?.role === "admin" && <button className={activeView === "access" ? "active" : ""} onClick={() => setActiveView("access")}><i>08</i>Accesos</button>}
          {canOperate && <button className={activeView === "metrics" ? "active" : ""} onClick={() => setActiveView("metrics")}><i>10</i>Métricas</button>}
          {canOperate && <button className={activeView === "pilot_operations" ? "active" : ""} onClick={() => setActiveView("pilot_operations")}><i>11</i>Piloto</button>}
          {canOperate && <button className={activeView === "final_report" ? "active" : ""} onClick={() => setActiveView("final_report")}><i>12</i>Cierre</button>}
        </nav>
        <div className="session-card">
          <span>{user.role}</span><b>{user.full_name}</b><small>{user.email}</small><button type="button" onClick={logout}>Cerrar sesión</button>
        </div>
      </aside>

      <section className="workspace">
        <header className="topbar">
          <div><p className="kicker">{viewTitle[0]}</p><h2>{viewTitle[1]}</h2></div>
          <div className="topbar-actions">
            <ApiStatus state={apiState} />
            {canOperate && <select value={selectedClientId} onChange={(event) => setSelectedClientId(event.target.value)} aria-label="Cliente activo">{clients.map((client) => <option key={client.id} value={client.id}>{client.name}</option>)}</select>}
            {canOperate && <button type="button" className="secondary" onClick={() => setShowClientForm(true)}>+ Nuevo cliente</button>}
          </div>
        </header>

        <Message value={message} onClose={() => setMessage(null)} />

        {activeView === "client_portal" ? (
          <ClientPortalPanel clientId={selectedClientId} userRole={user.role} request={request} download={download} onOpenChecklist={(invoice) => loadPayability(invoice)} />
        ) : activeView === "portfolio" ? (
          <>
            <section className="stats-grid" aria-label="Resumen de cartera">
              <Stat label="Facturas" value={invoices.length} note="en la cartera seleccionada" />
              <Stat label="Monto gestionado" value={money.format(metrics.total)} note="valor nominal total" />
              <Stat label="Vencidas abiertas" value={metrics.dueCount} note={money.format(metrics.dueAmount)} />
              <Stat label="Marcadas pagadas" value={metrics.paidCount} note="confirmación manual" />
              <Stat label="Pagables" value={metrics.payableCount} note="checklist completo" />
              <Stat label="En riesgo / reclamadas" value={metrics.riskCount} note="requieren atención" />
            </section>
            <section className="table-card">
              <div className="card-heading"><div><p className="kicker">{selectedClient?.rut ?? "CLIENTE"}</p><h3>{selectedClient?.name ?? "Mis facturas"}</h3></div><button type="button" className="ghost" onClick={loadInvoices}>Actualizar</button></div>
              <div className="table-wrap">
                <table>
                  <thead><tr><th>Folio</th><th>Pagador</th><th>Emisión</th><th>Vencimiento</th><th>Monto</th><th>OC</th><th>Estado</th><th>Pagabilidad</th><th>Flujo</th><th>Acción</th></tr></thead>
                  <tbody>
                    {invoices.map((invoice) => {
                      const workflow = workflowStateByInvoice.get(invoice.id);
                      const invoiceControl = controlByScope.get(`invoice:${invoice.id}`);
                      const payerControl = controlByScope.get(`payer:${invoice.payer_id}`);
                      const invoicePaused = invoiceControl?.status === "paused";
                      const payerPaused = payerControl?.status === "paused";
                      const automaticallyPaused = workflow?.status === "paused" && !invoicePaused && !payerPaused;
                      return (
                        <tr key={invoice.id}>
                          <td><b>{invoice.folio}</b><small>{invoice.document_type}</small></td><td>{invoice.payer_name}</td><td>{invoice.issued_on}</td><td>{invoice.due_on}</td>
                          <td className="number">{money.format(Number(invoice.total_amount))}</td><td>{invoice.purchase_order || <span className="missing">Sin OC</span>}</td>
                          <td><span className={`status-pill ${invoice.status}`}>{statusLabels[invoice.status]}</span></td>
                          <td><button type="button" className={`payability-pill ${invoice.payability_status}`} onClick={() => loadPayability(invoice)}>{payabilityLabels[invoice.payability_status]} · {invoice.payability_completed}/{invoice.payability_total}</button></td>
                          <td>{workflow ? <><b className="stage-label">{stageLabels[workflow.stage] ?? workflow.stage}</b><small>{workflow.status}{workflow.pause_reason ? ` · ${workflow.pause_reason}` : ""}</small></> : <span className="read-only">Sin evaluar</span>}</td>
                          <td className="row-actions">
                            {canOperate ? <>
                              <select className="status-select" value={invoice.status} onChange={(event) => updateStatus(invoice.id, event.target.value)}>{Object.entries(statusLabels).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select>
                              <button type="button" className="mini-button" disabled={automaticallyPaused || payerPaused || workflow?.status === "completed"} onClick={() => invoicePaused ? changeWorkflowControl({ scopeType: "invoice", scopeId: invoice.id, label: `Factura ${invoice.folio}` }, "resume") : setPauseTarget({ scopeType: "invoice", scopeId: invoice.id, label: `factura ${invoice.folio}` })}>{invoicePaused ? "Reanudar" : payerPaused ? "Pausa pagador" : "Pausar"}</button>
                            </> : <span className="read-only">Solo lectura</span>}
                            <button type="button" className="mini-button" onClick={() => showTimeline(invoice)}>Historial</button>
                          </td>
                        </tr>
                      );
                    })}
                    {!loadingInvoices && !invoices.length && <tr><td colSpan="10" className="empty">No hay facturas para este cliente.</td></tr>}
                    {loadingInvoices && <tr><td colSpan="10" className="empty">Cargando cartera…</td></tr>}
                  </tbody>
                </table>
              </div>
            </section>
            {canOperate && payerGroups.length > 0 && <section className="payer-card">
              <div className="card-heading"><div><p className="kicker">CONTROL MASIVO</p><h3>Gestión por pagador</h3></div><span className="read-only">La acción afecta todas sus facturas</span></div>
              <div className="payer-grid">{payerGroups.map((payer) => {
                const control = controlByScope.get(`payer:${payer.payerId}`);
                const paused = control?.status === "paused";
                return <article key={payer.payerId}><div><b>{payer.payerName}</b><span>{payer.invoices} facturas · {money.format(payer.amount)}</span>{paused && <small>Pausado: {control.reason}{control.resume_at ? ` · hasta ${new Date(control.resume_at).toLocaleString("es-CL")}` : ""}</small>}</div><button type="button" className="mini-button" onClick={() => paused ? changeWorkflowControl({ scopeType: "payer", scopeId: payer.payerId, label: `Pagador ${payer.payerName}` }, "resume") : setPauseTarget({ scopeType: "payer", scopeId: payer.payerId, label: `pagador ${payer.payerName}` })}>{paused ? "Reanudar pagador" : "Pausar pagador"}</button></article>;
              })}</div>
            </section>}
          </>
        ) : activeView === "imports" ? (
          <section className="imports-grid">
            <ImportPanel kind="invoices" clientId={selectedClientId} request={request} onImported={(count) => { setMessage({ type: "success", text: `${count} facturas importadas.` }); loadInvoices(); }} />
            <ImportPanel kind="contacts" clientId={selectedClientId} request={request} onImported={(count) => setMessage({ type: "success", text: `${count} contactos importados.` })} />
            <SiiImportPanel clientId={selectedClientId} request={request} onImported={(count) => { setMessage({ type: "success", text: `${count} estados SII actualizados.` }); loadInvoices(); }} />
          </section>
        ) : activeView === "contract" ? (
          <ContractPanel clientId={selectedClientId} request={request} />
        ) : activeView === "payability" ? (
          <PayabilityPanel clientId={selectedClientId} selectedClient={selectedClient} request={request} onClientUpdated={(updated) => setClients((current) => current.map((client) => client.id === updated.id ? updated : client))} />
        ) : activeView === "communications" ? (
          <CommunicationsPanel clientId={selectedClientId} request={request} />
        ) : activeView === "exceptions" ? (
          <ExceptionsPanel clientId={selectedClientId} request={request} />
        ) : activeView === "payments" ? (
          <PaymentsPanel clientId={selectedClientId} invoices={invoices} request={request} onChanged={loadInvoices} />
        ) : activeView === "metrics" ? (
          <MetricsPanel clientId={selectedClientId} request={request} download={download} />
        ) : activeView === "pilot_operations" ? (
          <PilotOperationsPanel clientId={selectedClientId} invoices={invoices} request={request} onOpenView={setActiveView} />
        ) : activeView === "final_report" ? (
          <FinalReportPanel request={request} download={download} user={user} />
        ) : (
          <AccessLogsPanel request={request} />
        )}
      </section>

      {showClientForm && <ClientForm request={request} onCancel={() => setShowClientForm(false)} onCreated={(client) => {
        setClients((current) => [...current, client].sort((a, b) => a.name.localeCompare(b.name)));
        setSelectedClientId(client.id);
        setShowClientForm(false);
        setMessage({ type: "success", text: `${client.name} fue creado correctamente.` });
      }} />}
      {pauseTarget && <PauseDialog target={pauseTarget} onCancel={() => setPauseTarget(null)} onConfirm={(reason, resumeAt) => changeWorkflowControl(pauseTarget, "pause", reason, resumeAt)} />}
      {timeline && <EventTimeline invoice={timeline} events={timelineEvents} loading={timelineLoading} onClose={() => setTimeline(null)} />}
      {payabilityChecklist && <PayabilityDialog checklist={payabilityChecklist} canOperate={canOperate} clientId={selectedClientId} request={request} onClose={() => setPayabilityChecklist(null)} onChanged={refreshPayability} />}
    </main>
  );
}
