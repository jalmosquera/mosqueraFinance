import { useEffect, useState } from "react";
import {
  apiErrorMessage,
  createFamilyRecord,
  deleteFamilyRecord,
  generatePaymentObligations,
  getMemberships,
  getNotificationPreference,
  getPaymentObligations,
  settlePaymentObligation,
  updateNotificationPreference,
  updateFamilyRecord,
  voidPaymentObligation
} from "./api";
import { formatMoney } from "./formatMoney";
import { formatDate } from "./formatDate";
import { browserPermission, clearLocalReminder, preferencePermission, requestBrowserPermission, scheduleLocalReminder } from "./notifications";
import { FinanceCrud, InitialConfiguration } from "./FinanceCrud";

const fieldClass = "mt-2 block w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-3 text-base text-white outline-none transition motion-reduce:transition-none focus:border-emerald-300";
const secondaryButtonClass = "min-h-11 rounded-xl border border-slate-700 px-3 py-2 text-sm font-semibold text-slate-200 disabled:cursor-not-allowed disabled:opacity-50";

function Message({ error, success }) {
  if (error) return <p aria-live="assertive" className="mt-4 rounded-xl border border-rose-900/60 bg-rose-950/30 px-3 py-2 text-sm text-rose-200" role="alert">{error}</p>;
  if (success) return <p aria-live="polite" className="mt-4 rounded-xl border border-emerald-900/60 bg-emerald-950/30 px-3 py-2 text-sm text-emerald-200" role="status">{success}</p>;
  return null;
}

function OwnerField({ value, onChange, disabled = false }) {
  return <label className="block text-sm font-medium text-slate-300">Visibilidad
    <select className={fieldClass} disabled={disabled} value={value} onChange={(event) => onChange(event.target.value)} required>
      <option value="">Elegí quién puede verla</option>
      <option value="shared">Compartida con la familia</option>
      <option value="private">Privada para mí</option>
    </select>
  </label>;
}

function Panel({ title, children }) {
  return <section className="rounded-[2rem] border border-slate-800 bg-slate-900/70 p-5 shadow-2xl shadow-slate-950/20"><h2 className="text-lg font-semibold text-white">{title}</h2>{children}</section>;
}

function NotificationPreferences({ familyId }) {
  const [preference, setPreference] = useState(null);
  const [permission, setPermission] = useState(browserPermission());
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    getNotificationPreference(familyId, controller.signal)
      .then((response) => setPreference(response))
      .catch(() => setError("No se pudieron cargar las preferencias de recordatorios."));
    return () => controller.abort();
  }, [familyId]);

  useEffect(() => {
    if (preference?.is_enabled && permission === "granted") {
      scheduleLocalReminder(preference.reminder_time);
    } else {
      clearLocalReminder();
    }
    return clearLocalReminder;
  }, [permission, preference]);

  async function save(next) {
    setSaving(true);
    setError("");
    try {
      const response = await updateNotificationPreference(familyId, next);
      setPreference(response);
    } catch (requestError) {
      setError(apiErrorMessage(requestError));
    } finally {
      setSaving(false);
    }
  }

  async function enable() {
    const nextPermission = await requestBrowserPermission();
    setPermission(nextPermission);
    if (nextPermission !== "granted") {
      setError(nextPermission === "unsupported" ? "Este navegador no admite notificaciones." : "El permiso de notificaciones no fue concedido.");
      await save({ is_enabled: false, permission: preferencePermission(nextPermission) });
      return;
    }
    await save({ is_enabled: true, permission: "GRANTED", reminder_time: preference.reminder_time || "09:00" });
  }

  if (!preference) return <Panel title="Recordatorios"><p aria-live="polite" className="mt-2 text-sm text-slate-400" role="status">Cargando preferencias...</p><Message error={error} /></Panel>;
  const isGranted = permission === "granted";
  return <Panel title="Recordatorios privados">
    <p className="mt-2 text-sm leading-6 text-slate-400">Activá recordatorios locales en este dispositivo. El aviso usa texto genérico y no incluye importes, cuentas ni movimientos.</p>
    <p className="mt-3 text-xs font-medium text-slate-500">Permiso del navegador: {permission === "granted" ? "concedido" : permission === "denied" ? "bloqueado" : permission === "unsupported" ? "no compatible" : "pendiente"}.</p>
    {preference.is_enabled && isGranted && <label className="mt-4 block text-sm font-medium text-slate-300">Hora del recordatorio<input className={fieldClass} onChange={(event) => setPreference((current) => ({ ...current, reminder_time: event.target.value }))} type="time" value={preference.reminder_time || "09:00"} /></label>}
    <div className="mt-4 grid grid-cols-2 gap-3">
      {!preference.is_enabled ? <button aria-busy={saving} className="rounded-xl bg-emerald-300 px-3 py-3 text-sm font-semibold text-slate-950 disabled:opacity-60" disabled={saving || permission === "unsupported"} onClick={enable} type="button">{saving ? "Guardando..." : "Activar"}</button> : <button aria-busy={saving} className="rounded-xl border border-rose-900/70 px-3 py-3 text-sm font-semibold text-rose-200 disabled:opacity-60" disabled={saving} onClick={() => save({ is_enabled: false, permission: preferencePermission(permission) })} type="button">Desactivar</button>}
      {preference.is_enabled && isGranted && <button className={secondaryButtonClass} disabled={saving} onClick={() => save({ is_enabled: true, permission: "GRANTED", reminder_time: preference.reminder_time || "09:00" })} type="button">Guardar hora</button>}
    </div>
    <Message error={error} />
    <p className="mt-4 text-xs leading-5 text-slate-500">La programación funciona mientras la app esté abierta. No se promete entrega en Apple Watch: requiere validar un dispositivo y su configuración.</p>
  </Panel>;
}

function NamedRecordsManager({ title, resource, records, sessionUser, familyId, onChanged, category = false }) {
  const [name, setName] = useState("");
  const [kind, setKind] = useState("EXPENSE");
  const [scope, setScope] = useState("");
  const [status, setStatus] = useState("idle");
  const [message, setMessage] = useState("");

  async function submit(event) {
    event.preventDefault();
    setStatus("saving");
    setMessage("");
    try {
      await createFamilyRecord(familyId, resource, {
        name: name.trim(),
        owner_id: scope === "shared" ? null : sessionUser.id,
        ...(category ? { kind } : {})
      });
      setName("");
      setScope("");
      setStatus("success");
      setMessage("Guardado.");
      onChanged();
    } catch (error) {
      setStatus("error");
      setMessage(apiErrorMessage(error));
    }
  }

  return <Panel title={title}>
    <p className="mt-2 text-sm leading-6 text-slate-400">{category ? "Clasificá ingresos y gastos antes de crear pronósticos." : "Representan el origen o destino lógico de los movimientos."}</p>
    <div className="mt-4 divide-y divide-slate-800">{records.length ? records.map((record) => <div className="flex items-center justify-between gap-3 py-3" key={record.id}><div className="min-w-0"><p className="truncate text-sm font-medium text-slate-200">{record.name}</p>{category && <p className="mt-1 text-xs text-slate-500">{record.kind === "INCOME" ? "Ingreso" : "Gasto"}</p>}</div><span className="shrink-0 text-xs font-medium text-slate-500">{record.owner_id ? "Privada" : "Compartida"}</span></div>) : <p className="py-3 text-sm text-slate-400">Todavía no hay registros visibles.</p>}</div>
    <form className="mt-4 border-t border-slate-800 pt-4" onSubmit={submit}>
      <label className="block text-sm font-medium text-slate-300">Nombre<input className={fieldClass} maxLength="120" onChange={(event) => setName(event.target.value)} required value={name} /></label>
      {category && <label className="mt-4 block text-sm font-medium text-slate-300">Tipo<select className={fieldClass} value={kind} onChange={(event) => setKind(event.target.value)}><option value="EXPENSE">Gasto</option><option value="INCOME">Ingreso</option></select></label>}
      <div className="mt-4"><OwnerField value={scope} onChange={setScope} /></div>
      <button aria-busy={status === "saving"} className="mt-4 w-full rounded-xl bg-emerald-300 px-4 py-3 text-sm font-semibold text-slate-950 disabled:cursor-not-allowed disabled:opacity-60" disabled={status === "saving"} type="submit">{status === "saving" ? "Guardando..." : `Crear ${category ? "categoría" : "cuenta"}`}</button>
      <Message error={status === "error" ? message : ""} success={status === "success" ? message : ""} />
    </form>
    <p className="mt-4 text-xs leading-5 text-slate-500">El API actual permite crear y consultar estos registros; sus cambios o eliminación no están disponibles.</p>
  </Panel>;
}

function ForecastForm({ type, accounts, categories, sessionUser, familyId, editing, onSaved, onCancel }) {
  const [form, setForm] = useState(() => editing ? { ...editing, scope: editing.owner_id ? "private" : "shared" } : { description: "", amount: "", occurred_on: "", effective_date: "", recurrence: "", account_id: "", category_id: "", scope: "" });
  const [error, setError] = useState("");
  const [saving, setSaving] = useState(false);
  const resource = type === "income" ? "income-forecasts" : "expense-forecasts";
  const usableCategories = categories.filter((category) => category.kind === (type === "income" ? "INCOME" : "EXPENSE"));

  function setValue(name, value) { setForm((current) => ({ ...current, [name]: value })); }
  async function submit(event) {
    event.preventDefault();
    setSaving(true); setError("");
    const payload = { description: form.description, amount: form.amount.replace(",", "."), occurred_on: form.occurred_on, effective_date: form.effective_date, recurrence: form.recurrence, account_id: Number(form.account_id), category_id: Number(form.category_id), owner_id: form.scope === "shared" ? null : sessionUser.id };
    try {
      if (editing) await updateFamilyRecord(familyId, resource, editing.id, payload);
      else await createFamilyRecord(familyId, resource, payload);
      onSaved();
    } catch (requestError) { setError(apiErrorMessage(requestError)); } finally { setSaving(false); }
  }
  return <form className="mt-4 space-y-4 border-t border-slate-800 pt-4" onSubmit={submit}>
    <label className="block text-sm font-medium text-slate-300">Descripción<input className={fieldClass} maxLength="255" onChange={(event) => setValue("description", event.target.value)} value={form.description} /></label>
    <label className="block text-sm font-medium text-slate-300">Importe<input aria-describedby="amount-format" className={fieldClass} inputMode="decimal" onChange={(event) => setValue("amount", event.target.value)} pattern="[0-9]+([,.][0-9]{1,2})?" placeholder="0,00" required type="text" value={form.amount} /></label>
    <p className="-mt-2 text-xs text-slate-500" id="amount-format">Usá coma o punto para los decimales.</p>
    <OwnerField disabled={Boolean(editing)} value={form.scope} onChange={(value) => setValue("scope", value)} />
    <label className="block text-sm font-medium text-slate-300">Cuenta<select className={fieldClass} onChange={(event) => setValue("account_id", event.target.value)} required value={form.account_id}><option value="">Elegí una cuenta</option>{accounts.map((account) => <option key={account.id} value={account.id}>{account.name}</option>)}</select></label>
    <label className="block text-sm font-medium text-slate-300">Categoría<select className={fieldClass} onChange={(event) => setValue("category_id", event.target.value)} required value={form.category_id}><option value="">Elegí una categoría</option>{usableCategories.map((category) => <option key={category.id} value={category.id}>{category.name}</option>)}</select></label>
    <label className="block text-sm font-medium text-slate-300">Fecha prevista<input className={fieldClass} onChange={(event) => setValue("occurred_on", event.target.value)} required type="date" value={form.occurred_on} /></label>
    <label className="block text-sm font-medium text-slate-300">Vigente desde<input className={fieldClass} onChange={(event) => setValue("effective_date", event.target.value)} required type="date" value={form.effective_date} /></label>
    <label className="block text-sm font-medium text-slate-300">Repetición<select className={fieldClass} onChange={(event) => setValue("recurrence", event.target.value)} required value={form.recurrence}><option value="">Elegí una repetición</option><option value="NONE">Sin repetición</option><option value="MONTHLY">Mensual</option></select></label>
    <Message error={error} />
    <div className="grid grid-cols-2 gap-3"><button aria-busy={saving} className="rounded-xl bg-emerald-300 px-4 py-3 text-sm font-semibold text-slate-950 disabled:opacity-60" disabled={saving} type="submit">{saving ? "Guardando..." : editing ? "Guardar" : "Crear pronóstico"}</button>{editing && <button className={secondaryButtonClass} onClick={onCancel} type="button">Cancelar</button>}</div>
  </form>;
}

function ForecastManager({ type, records, accounts, categories, sessionUser, familyId, onChanged }) {
  const [editing, setEditing] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [error, setError] = useState("");
  const title = type === "income" ? "Pronósticos de ingreso" : "Pronósticos de gasto";
  const resource = type === "income" ? "income-forecasts" : "expense-forecasts";
  async function remove(record) {
    if (!window.confirm("¿Eliminar este pronóstico? Las ocurrencias históricas no se modifican.")) return;
    setError("");
    try { await deleteFamilyRecord(familyId, resource, record.id); onChanged(); } catch (requestError) { setError(apiErrorMessage(requestError)); }
  }
  function saved() { setEditing(null); setShowForm(false); onChanged(); }
  return <Panel title={title}>
    <p className="mt-2 text-sm leading-6 text-slate-400">Los cambios preservan las ocurrencias históricas que ya se generaron.</p>
    <div className="mt-4 divide-y divide-slate-800">{records.length ? records.map((record) => <div className="py-3" key={record.id}><div className="flex justify-between gap-3"><div className="min-w-0"><p className="truncate text-sm font-medium text-slate-200">{record.description || "Sin descripción"}</p><p className="mt-1 text-xs text-slate-500">{record.recurrence} · {record.owner_id ? "Privado" : "Compartido"}</p></div><p className="shrink-0 text-sm font-semibold text-white">{formatMoney(record.amount)}</p></div><div className="mt-3 flex gap-2"><button className={secondaryButtonClass} onClick={() => { setEditing(record); setShowForm(false); }} type="button">Editar</button><button className="rounded-xl border border-rose-900/70 px-3 py-2 text-sm font-semibold text-rose-200" onClick={() => remove(record)} type="button">Eliminar</button></div></div>) : <p className="py-3 text-sm text-slate-400">Todavía no hay pronósticos visibles.</p>}</div>
    {!editing && !showForm && <button className="mt-4 w-full rounded-xl bg-emerald-300 px-4 py-3 text-sm font-semibold text-slate-950" onClick={() => setShowForm(true)} type="button">Agregar pronóstico</button>}
    {(editing || showForm) && <ForecastForm accounts={accounts} categories={categories} editing={editing} familyId={familyId} onCancel={() => { setEditing(null); setShowForm(false); }} onSaved={saved} sessionUser={sessionUser} type={type} />}
    <Message error={error} />
  </Panel>;
}

function Obligations({ familyId, memberships }) {
  const [month, setMonth] = useState("");
  const [records, setRecords] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [voiding, setVoiding] = useState(null);
  const [reason, setReason] = useState("");
  async function load(generate = false) {
    if (!month) return;
    setLoading(true); setError("");
    const sourcePeriod = `${month}-01`;
    try { setRecords(generate ? await generatePaymentObligations(familyId, sourcePeriod) : await getPaymentObligations(familyId, sourcePeriod)); } catch (requestError) { setError(apiErrorMessage(requestError)); } finally { setLoading(false); }
  }
  async function settle(record) {
    setError("");
    try { await settlePaymentObligation(familyId, record.id); await load(); } catch (requestError) { setError(apiErrorMessage(requestError)); }
  }
  async function submitVoid(event, record) {
    event.preventDefault(); setError("");
    try { await voidPaymentObligation(familyId, record.id, reason); setVoiding(null); setReason(""); await load(); } catch (requestError) { setError(apiErrorMessage(requestError)); }
  }
  return <Panel title="Obligaciones recurrentes">
    <p className="mt-2 text-sm leading-6 text-slate-400">Se generan desde los pronósticos recurrentes. Liquidar confirma el movimiento; anular requiere un motivo y mantiene la auditoría.</p>
    <label className="mt-4 block text-sm font-medium text-slate-300">Mes<input className={fieldClass} onChange={(event) => setMonth(event.target.value)} required type="month" value={month} /></label>
    <div className="mt-4 grid grid-cols-2 gap-3"><button className={secondaryButtonClass} disabled={!month || loading} onClick={() => load()} type="button">Consultar</button><button className="rounded-xl bg-emerald-300 px-3 py-2 text-sm font-semibold text-slate-950 disabled:opacity-60" disabled={!month || loading} onClick={() => load(true)} type="button">Generar</button></div>
    <Message error={error} />
    <div className="mt-4 divide-y divide-slate-800">{records.map((record) => <article className="py-4" key={record.id}><div className="flex justify-between gap-3"><div><p className="text-sm font-medium text-slate-200">{record.description || "Sin descripción"}</p><p className="mt-1 text-xs text-slate-500">Vence {formatDate(record.due_on)} · {record.status}</p></div><p className="text-sm font-semibold text-white">{formatMoney(record.amount)}</p></div>{record.status === "PENDING" && <div className="mt-3 flex gap-2"><button className={secondaryButtonClass} onClick={() => settle(record)} type="button">Liquidar</button><button className="rounded-xl border border-rose-900/70 px-3 py-2 text-sm font-semibold text-rose-200" onClick={() => setVoiding(record)} type="button">Anular</button></div>}{voiding?.id === record.id && <form className="mt-3" onSubmit={(event) => submitVoid(event, record)}><label className="block text-sm font-medium text-slate-300">Motivo<textarea className={fieldClass} maxLength="1000" onChange={(event) => setReason(event.target.value)} required value={reason} /></label><div className="mt-3 flex gap-2"><button className="rounded-xl bg-rose-300 px-3 py-2 text-sm font-semibold text-slate-950" type="submit">Confirmar anulación</button><button className={secondaryButtonClass} onClick={() => setVoiding(null)} type="button">Cancelar</button></div></form>}</article>)}</div>
    {records.length === 0 && month && !loading && <p className="mt-4 text-sm text-slate-400">No hay obligaciones visibles para este mes.</p>}
    {memberships.length === 0 && <p className="mt-4 text-xs text-slate-500">No se pudieron cargar los integrantes autorizados. Las liquidaciones compartidas pueden requerir asignaciones del API.</p>}
  </Panel>;
}

export function Settings({ accounts, categories, data, familyId, families, incomeForecasts, expenseForecasts, isAdmin, onChanged, onFamilyChange, onLogout, sessionUser }) {
  const [panel, setPanel] = useState("profile");
  const [memberships, setMemberships] = useState([]);
  useEffect(() => {
    if (!familyId) return undefined;
    const controller = new AbortController();
    getMemberships(familyId, controller.signal).then(setMemberships).catch(() => setMemberships([]));
    return () => controller.abort();
  }, [familyId]);
  const panels = [{ id: "profile", label: "Perfil" }, { id: "notifications", label: "Avisos" }, { id: "categories", label: "Categorías" }, { id: "accounts", label: "Cuentas" }, { id: "forecasts", label: "Pronósticos" }, { id: "movements", label: "Reales" }, { id: "savings", label: "Ahorros" }, { id: "setup", label: "Inicial" }, { id: "obligations", label: "Obligaciones" }];
  return <div className="mt-8 space-y-5">
    <div className="flex gap-2 overflow-x-auto pb-1" role="tablist" aria-label="Ajustes">{panels.map((item) => <button aria-controls="settings-panel" aria-selected={panel === item.id} className={`shrink-0 rounded-xl px-3 py-2 text-sm font-semibold ${panel === item.id ? "bg-emerald-300 text-slate-950" : "bg-slate-900 text-slate-400"}`} id={`settings-tab-${item.id}`} key={item.id} onClick={() => setPanel(item.id)} role="tab" tabIndex={panel === item.id ? 0 : -1} type="button">{item.label}</button>)}</div>
    <div aria-labelledby={`settings-tab-${panel}`} id="settings-panel" role="tabpanel">
    {panel === "profile" && <Panel title="Perfil y familia"><dl className="mt-4 space-y-3 text-sm"><div><dt className="text-slate-500">Usuario</dt><dd className="mt-1 font-medium text-slate-100">{sessionUser.username}</dd></div>{sessionUser.email && <div><dt className="text-slate-500">Correo</dt><dd className="mt-1 font-medium text-slate-100">{sessionUser.email}</dd></div>}</dl>{families.length > 1 && <label className="mt-5 block text-sm font-medium text-slate-300">Familia activa<select className={fieldClass} onChange={(event) => onFamilyChange(event.target.value)} value={familyId}>{families.map((family) => <option key={family.id} value={family.id}>{family.name}</option>)}</select></label>}<button className="mt-6 w-full rounded-xl border border-rose-900/70 px-4 py-3 text-sm font-semibold text-rose-200" onClick={onLogout} type="button">Cerrar sesión</button></Panel>}
    {panel === "notifications" && <NotificationPreferences familyId={familyId} />}
    {panel === "categories" && <NamedRecordsManager category familyId={familyId} onChanged={onChanged} records={categories} resource="categories" sessionUser={sessionUser} title="Categorías" />}
    {panel === "accounts" && <NamedRecordsManager familyId={familyId} onChanged={onChanged} records={accounts} resource="logical-accounts" sessionUser={sessionUser} title="Cuentas lógicas" />}
    {panel === "forecasts" && <><ForecastManager accounts={accounts} categories={categories} familyId={familyId} onChanged={onChanged} records={incomeForecasts} sessionUser={sessionUser} type="income" /><div className="h-5" /><ForecastManager accounts={accounts} categories={categories} familyId={familyId} onChanged={onChanged} records={expenseForecasts} sessionUser={sessionUser} type="expense" /></>}
    {panel === "movements" && data && <FinanceCrud accounts={accounts} categories={categories} data={data} familyId={familyId} isAdmin={isAdmin} memberships={memberships} onChanged={onChanged} sessionUser={sessionUser} showSavings={false} />}
    {panel === "savings" && data && <FinanceCrud accounts={accounts} categories={categories} data={data} familyId={familyId} isAdmin={isAdmin} memberships={memberships} onChanged={onChanged} sessionUser={sessionUser} showMovements={false} />}
    {panel === "setup" && <InitialConfiguration familyId={familyId} isAdmin={isAdmin} memberships={memberships} onSaved={onChanged} />}
    {panel === "obligations" && <Obligations familyId={familyId} memberships={memberships} />}
    </div>
  </div>;
}
