import { useEffect, useState } from "react";
import { bootstrapSession, getFamilies, getFamilyData, getMemberships, isForbidden, isUnauthenticated, login, logout } from "./api";
import { createExportImage, downloadImage } from "./exportImage";
import { createExportPayload } from "./exportPayload";
import { formatDate, formatMonth } from "./formatDate";
import { formatMoney } from "./formatMoney";
import { Settings } from "./Settings";

export { formatMoney };

const tabs = ["Resumen", "Detalle", "Proyección"];
const navigation = [
  { label: "Inicio", icon: "home" },
  { label: "Gastos", icon: "receipt" },
  { label: "Ahorros", icon: "leaf" },
  { label: "Ajustes", icon: "settings" }
];

function Icon({ name }) {
  const paths = {
    home: <path d="m3 10 9-7 9 7v9a2 2 0 0 1-2 2h-4v-6H9v6H5a2 2 0 0 1-2-2z" />,
    receipt: <path d="M6 3h12v18l-3-2-3 2-3-2-3 2zM9 8h6M9 12h6" />,
    leaf: <path d="M20 4C11 4 5 8.5 5 15c0 3 2 5 5 5 6.5 0 10-6 10-16ZM4 21c3-5 7-8 12-10" />,
    settings: <path d="M12 15.25A3.25 3.25 0 1 0 12 8.75a3.25 3.25 0 0 0 0 6.5Z M19.4 15a1.7 1.7 0 0 0 .34 1.87l.06.06-2.12 2.12-.06-.06a1.7 1.7 0 0 0-1.87-.34 1.7 1.7 0 0 0-1.03 1.56v.09h-3v-.09A1.7 1.7 0 0 0 10.7 18.65a1.7 1.7 0 0 0-1.87.34l-.06.06-2.12-2.12.06-.06A1.7 1.7 0 0 0 7.05 15a1.7 1.7 0 0 0-1.56-1.03H5.4v-3h.09A1.7 1.7 0 0 0 7.05 9.94 1.7 1.7 0 0 0 6.7 8.07l-.06-.06 2.12-2.12.06.06a1.7 1.7 0 0 0 1.87.34 1.7 1.7 0 0 0 1.03-1.56v-.09h3v.09a1.7 1.7 0 0 0 1.03 1.56 1.7 1.7 0 0 0 1.87-.34l.06-.06 2.12 2.12-.06.06a1.7 1.7 0 0 0-.34 1.87 1.7 1.7 0 0 0 1.56 1.03h.09v3h-.09A1.7 1.7 0 0 0 19.4 15Z" />
  };

  return <svg viewBox="0 0 24 24" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round">{paths[name]}</svg>;
}

function EmptyState({ children }) {

  return (
    <section className="rounded-[2rem] border border-slate-800 bg-slate-900/70 p-6 shadow-2xl shadow-slate-950/30">
      <div className="mb-5 flex h-12 w-12 items-center justify-center rounded-2xl bg-emerald-400/10 text-emerald-300">
        <svg viewBox="0 0 24 24" className="h-6 w-6" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="1.7"><path d="M12 3v18M3 12h18" strokeLinecap="round" /></svg>
      </div>
      <h2 className="text-lg font-semibold text-white">Todavía no hay información para mostrar</h2>
      <p className="mt-2 max-w-sm text-sm leading-6 text-slate-400">{children}</p>
    </section>
  );
}

function Records({ title, items, children }) {
  return (
    <section className="rounded-[2rem] border border-slate-800 bg-slate-900/70 p-5 shadow-2xl shadow-slate-950/20">
      <div className="flex items-center justify-between gap-3">
        <h2 className="text-base font-semibold text-white">{title}</h2>
        <span className="text-xs font-medium text-slate-500">{items.length}</span>
      </div>
      {items.length ? <div className="mt-4 divide-y divide-slate-800">{children}</div> : <p className="mt-3 text-sm text-slate-400">Aún no se configuró información.</p>}
    </section>
  );
}

function MoneyRecord({ record, subtitle, amount = record.amount }) {
  return (
    <article className="flex items-start justify-between gap-4 py-3 first:pt-0 last:pb-0">
      <div className="min-w-0">
        <p className="truncate text-sm font-medium text-slate-200">{record.description || "Sin descripción"}</p>
        {subtitle && <p className="mt-1 text-xs text-slate-500">{subtitle}</p>}
      </div>
      {amount !== undefined && <p className="shrink-0 text-sm font-semibold text-white">{formatMoney(amount)}</p>}
    </article>
  );
}

function firstDayOfCurrentMonth() {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-01`;
}

function LoginScreen({ onAuthenticated }) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [status, setStatus] = useState("idle");

  async function submit(event) {
    event.preventDefault();
    setStatus("submitting");
    try {
      onAuthenticated(await login(username, password));
    } catch {
      setStatus("error");
    }
  }

  return (
    <main className="flex min-h-dvh items-center bg-slate-950 pb-[max(2rem,env(safe-area-inset-bottom))] pl-[max(1.25rem,env(safe-area-inset-left))] pr-[max(1.25rem,env(safe-area-inset-right))] pt-[max(2rem,env(safe-area-inset-top))] text-slate-100">
      <section className="mx-auto w-full max-w-md rounded-[2rem] border border-slate-800 bg-slate-900/70 p-6 shadow-2xl shadow-slate-950/40">
        <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-emerald-400/10 text-lg font-bold text-emerald-300">MF</div>
        <p className="mt-6 text-xs font-semibold uppercase tracking-[0.2em] text-emerald-300">Mosquera Finance</p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight text-white">Tu espacio familiar</h1>
        <p className="mt-3 text-sm leading-6 text-slate-400">Ingresá para consultar la información que tenés autorizada.</p>
        <form className="mt-7 space-y-4" onSubmit={submit}>
          <label className="block text-sm font-medium text-slate-300">Usuario<input autoComplete="username" className="mt-2 block w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-3 text-base text-white outline-none transition motion-reduce:transition-none focus:border-emerald-300" onChange={(event) => setUsername(event.target.value)} required value={username} /></label>
          <label className="block text-sm font-medium text-slate-300">Contraseña<input autoComplete="current-password" className="mt-2 block w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-3 text-base text-white outline-none transition motion-reduce:transition-none focus:border-emerald-300" onChange={(event) => setPassword(event.target.value)} required type="password" value={password} /></label>
          {status === "error" && <p className="rounded-xl border border-rose-900/60 bg-rose-950/30 px-3 py-2 text-sm text-rose-200" role="alert">No se pudo iniciar sesión. Verificá tus datos e intentá nuevamente.</p>}
          <button aria-busy={status === "submitting"} className="w-full rounded-xl bg-emerald-300 px-4 py-3 text-sm font-semibold text-slate-950 transition motion-reduce:transition-none hover:bg-emerald-200 disabled:cursor-not-allowed disabled:opacity-60" disabled={status === "submitting"} type="submit">{status === "submitting" ? "Ingresando..." : "Iniciar sesión"}</button>
        </form>
        <p className="mt-5 text-center text-xs leading-5 text-slate-500">Tu sesión se mantiene protegida en este dispositivo.</p>
      </section>
    </main>
  );
}

function FirstRunOnboarding({ isAdmin, onConfigure, reviewed, setReviewed }) {
  if (!isAdmin) {
    return (
      <section className="rounded-[2rem] border border-amber-900/60 bg-amber-950/20 p-6" role="status">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-amber-300">Acceso limitado</p>
        <h2 className="mt-2 text-lg font-semibold text-white">La configuración inicial la administra Jalberth</h2>
        <p className="mt-3 text-sm leading-6 text-slate-400">Vas a ver únicamente los datos compartidos y los tuyos que estén autorizados. Los ingresos, gastos, ahorros, proyecciones y exportaciones privados de Jalberth no se muestran en tu cuenta.</p>
      </section>
    );
  }

  return (
    <section className="rounded-[2rem] border border-emerald-900/50 bg-emerald-950/20 p-6">
      <p className="text-xs font-semibold uppercase tracking-[0.2em] text-emerald-300">Configuración inicial</p>
      <h2 className="mt-2 text-xl font-semibold text-white">Primero definí el plan, después registrá lo real</h2>
      <div className="mt-4 space-y-3 text-sm leading-6 text-slate-400">
        <p>Los pronósticos describen importes previstos y sirven para planificar. No son movimientos confirmados ni modifican los saldos reales.</p>
        <p>Los movimientos reales se registran cuando ocurren. Conservan su historial y se corrigen con operaciones auditadas, no eliminándolos.</p>
      </div>
      <label className="mt-5 flex cursor-pointer items-start gap-3 rounded-xl border border-slate-700 bg-slate-950/50 p-4 text-sm leading-5 text-slate-300">
        <input checked={reviewed} className="mt-0.5 h-5 min-h-0 w-5 shrink-0 accent-emerald-300" onChange={(event) => setReviewed(event.target.checked)} type="checkbox" />
        <span>Revisé la diferencia entre pronósticos y movimientos reales. Confirmo que voy a verificar la información antes de guardarla.</span>
      </label>
      <button className="mt-4 w-full rounded-xl bg-emerald-300 px-4 py-3 text-sm font-semibold text-slate-950 disabled:cursor-not-allowed disabled:opacity-60" disabled={!reviewed} onClick={onConfigure} type="button">Ir a la configuración inicial</button>
      <p className="mt-3 text-xs leading-5 text-slate-500">La configuración inicial crea solo datos de planificación; los movimientos reales se registran por separado.</p>
    </section>
  );
}

function ExportCards({ data, familyName, sessionUser }) {
  const [recipient, setRecipient] = useState("Raiza");
  const [status, setStatus] = useState("idle");
  const [error, setError] = useState("");

  async function exportCards() {
    setStatus("loading");
    setError("");
    const recipients = recipient === "both" ? ["Raiza", "Jalberth"] : [recipient];

    try {
      const files = await Promise.all(recipients.map(async (name) => {
        const payload = createExportPayload(data, sessionUser, name);
        const blob = await createExportImage(payload, familyName);
        return new File([blob], `resumen-${name.toLocaleLowerCase()}.png`, { type: "image/png" });
      }));

      if (navigator.share && navigator.canShare?.({ files })) {
        await navigator.share({ files, title: "Resumen financiero" });
        setStatus("shared");
      } else {
        files.forEach(downloadImage);
        setStatus("downloaded");
      }
    } catch (exportError) {
      if (exportError.name === "AbortError") {
        setStatus("idle");
        return;
      }
      setError("No se pudieron generar las tarjetas. Intentá nuevamente.");
      setStatus("error");
    }
  }

  return (
    <section className="rounded-[2rem] border border-emerald-900/50 bg-emerald-950/20 p-5">
      <h2 className="text-base font-semibold text-white">Compartir resumen privado</h2>
      <p className="mt-2 text-sm leading-6 text-slate-400">Se crea una tarjeta PNG por destinatario. La tarjeta de Raiza solo incluye datos compartidos y sus propios datos autorizados.</p>
      <fieldset className="mt-4 grid grid-cols-3 gap-2" disabled={status === "loading"}>
        <legend className="sr-only">Destinatario</legend>
        {[{ value: "Raiza", label: "Raiza" }, { value: "Jalberth", label: "Jalberth" }, { value: "both", label: "Ambos" }].map((option) => <label key={option.value} className={`flex min-h-11 cursor-pointer items-center justify-center rounded-xl border px-2 py-2 text-xs font-semibold focus-within:outline-2 focus-within:outline-offset-3 focus-within:outline-emerald-300 ${recipient === option.value ? "border-emerald-300 bg-emerald-300 text-slate-950" : "border-slate-700 text-slate-300"}`}><input checked={recipient === option.value} className="sr-only" name="export-recipient" onChange={() => setRecipient(option.value)} type="radio" value={option.value} />{option.label}</label>)}
      </fieldset>
      {error && <p className="mt-3 text-sm text-rose-200" role="alert">{error}</p>}
      {status === "shared" && <p className="mt-3 text-sm text-emerald-200" role="status">Tarjeta compartida.</p>}
      {status === "downloaded" && <p className="mt-3 text-sm text-emerald-200" role="status">La descarga empezó porque compartir archivos no está disponible.</p>}
      <button aria-busy={status === "loading"} type="button" onClick={exportCards} disabled={status === "loading"} className="mt-4 w-full rounded-xl bg-emerald-300 px-4 py-3 text-sm font-semibold text-slate-950 disabled:cursor-not-allowed disabled:opacity-60">{status === "loading" ? "Generando tarjetas..." : "Generar y compartir PNG"}</button>
    </section>
  );
}

export function App() {
  const [activeTab, setActiveTab] = useState("Resumen");
  const [activeSection, setActiveSection] = useState("Inicio");
  const [families, setFamilies] = useState([]);
  const [familyId, setFamilyId] = useState("");
  const [data, setData] = useState(null);
  const [loadedFamilyId, setLoadedFamilyId] = useState("");
  const [state, setState] = useState("loading");
  const [session, setSession] = useState({ status: "loading", user: null });
  const [reloadKey, setReloadKey] = useState(0);
  const [memberships, setMemberships] = useState([]);
  const [membershipsLoadedFor, setMembershipsLoadedFor] = useState("");
  const [initialConfigurationReviewed, setInitialConfigurationReviewed] = useState(false);

  function loadFamilies() {
    const controller = new AbortController();
    setState("loading");
    getFamilies(controller.signal)
      .then((response) => {
        setFamilies(response);
        setFamilyId((current) => current || String(response[0]?.id || ""));
        setState(response.length ? "ready" : "empty");
      })
      .catch((error) => {
        if (error.code !== "ERR_CANCELED") {
          setState(isUnauthenticated(error) ? "unauthenticated" : isForbidden(error) ? "forbidden" : "error");
        }
      });
    return () => controller.abort();
  }

  function retry() {
    setData(null);
    setLoadedFamilyId("");
    setFamilyId("");
    loadFamilies();
  }

  function reloadFamilyData() {
    setReloadKey((current) => current + 1);
  }

  useEffect(() => {
    const controller = new AbortController();
    bootstrapSession(controller.signal)
      .then((user) => setSession({ status: "authenticated", user }))
      .catch((error) => {
        if (error.code !== "ERR_CANCELED") {
          setSession({ status: "unauthenticated", user: null });
        }
      });
    return () => controller.abort();
  }, []);

  useEffect(() => {
    if (session.status !== "authenticated") {
      return undefined;
    }
    return loadFamilies();
  }, [session.status]);

  useEffect(() => {
    if (session.status !== "authenticated" || !familyId) {
      return undefined;
    }

    const controller = new AbortController();
    setData(null);
    setLoadedFamilyId("");
    setState("loading");
    getFamilyData(familyId, firstDayOfCurrentMonth(), controller.signal)
      .then((response) => {
        setData(response);
        setLoadedFamilyId(familyId);
        setState("ready");
      })
      .catch((error) => {
        if (error.code !== "ERR_CANCELED") {
          setState(isUnauthenticated(error) ? "unauthenticated" : isForbidden(error) ? "forbidden" : "error");
        }
      });
    return () => controller.abort();
  }, [familyId, reloadKey, session.status]);

  useEffect(() => {
    if (session.status !== "authenticated" || !familyId) {
      setMemberships([]);
      setMembershipsLoadedFor("");
      return undefined;
    }

    const controller = new AbortController();
    setMemberships([]);
    setMembershipsLoadedFor("");
    getMemberships(familyId, controller.signal)
      .then((response) => {
        setMemberships(response);
        setMembershipsLoadedFor(familyId);
      })
      .catch(() => {
        if (!controller.signal.aborted) {
          setMembershipsLoadedFor(familyId);
        }
      });
    return () => controller.abort();
  }, [familyId, session.status]);

  async function signOut() {
    try {
      await logout();
    } finally {
      setData(null);
      setLoadedFamilyId("");
      setFamilies([]);
      setFamilyId("");
      setSession({ status: "unauthenticated", user: null });
    }
  }

  function handleAuthenticated(user) {
    setSession({ status: "authenticated", user });
  }

  const selectedFamily = families.find((family) => String(family.id) === familyId);
  const showProjection = activeTab === "Proyección";
  const visibleData = loadedFamilyId === familyId ? data : null;
  const currentMembership = memberships.find((membership) => membership.user_id === session.user?.id && membership.is_active);
  const isAdmin = currentMembership?.role === "ADMIN";
  const isFirstRun = Boolean(visibleData) && !visibleData.accounts.length && !visibleData.categories.length && !visibleData.incomeForecasts.length && !visibleData.expenseForecasts.length;
  const shouldShowOnboarding = state === "ready" && visibleData && membershipsLoadedFor === familyId && isFirstRun && !initialConfigurationReviewed;

  function openInitialConfiguration() {
    setActiveSection("Ajustes");
    setInitialConfigurationReviewed(true);
  }

  if (session.status === "loading") {
    return <main aria-live="polite" className="flex min-h-dvh items-center justify-center bg-slate-950 px-5 text-sm font-medium text-slate-300" role="status">Preparando sesión segura...</main>;
  }

  if (session.status === "unauthenticated") {
    return <LoginScreen onAuthenticated={handleAuthenticated} />;
  }

  return (
    <main className="min-h-dvh bg-slate-950 text-slate-100">
      <div className="mx-auto flex min-h-dvh max-w-md flex-col px-5 pb-28 pt-[max(1.5rem,env(safe-area-inset-top))]">
        <header className="flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-emerald-300">Mosquera Finance</p>
            <h1 className="mt-2 text-3xl font-semibold tracking-tight text-white">{selectedFamily?.name || activeSection}</h1>
          </div>
          <button className="flex h-11 min-w-11 items-center justify-center rounded-full border border-slate-800 bg-slate-900 px-2 text-sm font-semibold text-slate-300" onClick={signOut} type="button" aria-label="Cerrar sesión">{session.user.username.slice(0, 2).toUpperCase()}</button>
        </header>

        {families.length > 1 && activeSection !== "Ajustes" && <label className="mt-6 block text-sm text-slate-400">Familia<select value={familyId} onChange={(event) => setFamilyId(event.target.value)} className="mt-2 block w-full rounded-xl border border-slate-800 bg-slate-900 px-3 py-3 text-sm font-medium text-white">{families.map((family) => <option key={family.id} value={family.id}>{family.name}</option>)}</select></label>}

        {activeSection !== "Ajustes" && <div className="mt-8 flex rounded-2xl bg-slate-900 p-1" aria-label="Vista financiera">
          {tabs.map((tab) => (
            <button
              key={tab}
              type="button"
              onClick={() => setActiveTab(tab)}
              className={`flex-1 rounded-xl px-2 py-2.5 text-xs font-semibold transition motion-reduce:transition-none ${activeTab === tab ? "bg-slate-700 text-white shadow-sm" : "text-slate-500"}`}
            >
              {tab}
            </button>
          ))}
        </div>}

        <div className="mt-6">
          {activeSection === "Ajustes" && shouldShowOnboarding && <FirstRunOnboarding isAdmin={isAdmin} onConfigure={openInitialConfiguration} reviewed={initialConfigurationReviewed} setReviewed={setInitialConfigurationReviewed} />}
          {activeSection === "Ajustes" && familyId && !shouldShowOnboarding && <Settings accounts={visibleData?.accounts || []} categories={visibleData?.categories || []} data={visibleData} expenseForecasts={visibleData?.expenseForecasts || []} families={families} familyId={familyId} incomeForecasts={visibleData?.incomeForecasts || []} isAdmin={isAdmin} onChanged={reloadFamilyData} onFamilyChange={setFamilyId} onLogout={signOut} sessionUser={session.user} />}
          {activeSection !== "Ajustes" && state === "loading" && <section className="rounded-[2rem] border border-slate-900 bg-slate-900/40 p-5" aria-live="polite" role="status"><p className="text-sm font-medium text-slate-300">Cargando información protegida</p><div className="mt-4 space-y-3" aria-hidden="true"><div className="h-3 w-2/5 animate-pulse motion-reduce:animate-none rounded-full bg-slate-800" /><div className="h-3 w-full animate-pulse motion-reduce:animate-none rounded-full bg-slate-800" /></div></section>}
          {activeSection !== "Ajustes" && state === "unauthenticated" && <EmptyState>Tu sesión no está disponible. Iniciá sesión para consultar la información autorizada.</EmptyState>}
          {activeSection !== "Ajustes" && state === "forbidden" && <section className="rounded-[2rem] border border-amber-900/60 bg-amber-950/20 p-6" role="alert"><h2 className="text-lg font-semibold text-white">No tenés acceso a esta información</h2><p className="mt-2 text-sm leading-6 text-slate-400">Por privacidad, no mostramos detalles de datos que no están autorizados para tu perfil.</p><button type="button" onClick={retry} className="mt-5 rounded-xl bg-amber-300 px-4 py-2 text-sm font-semibold text-slate-950">Reintentar</button></section>}
          {activeSection !== "Ajustes" && state === "error" && <section className="rounded-[2rem] border border-rose-900/60 bg-rose-950/30 p-6" role="alert"><h2 className="text-lg font-semibold text-white">No se pudo cargar la información</h2><p className="mt-2 text-sm leading-6 text-slate-400">Verificá la conexión e intentá nuevamente.</p><button type="button" onClick={retry} className="mt-5 rounded-xl bg-rose-300 px-4 py-2 text-sm font-semibold text-slate-950">Reintentar</button></section>}
          {activeSection !== "Ajustes" && state === "empty" && <EmptyState>No tenés una familia autorizada para consultar.</EmptyState>}
          {activeSection !== "Ajustes" && shouldShowOnboarding && <FirstRunOnboarding isAdmin={isAdmin} onConfigure={openInitialConfiguration} reviewed={initialConfigurationReviewed} setReviewed={setInitialConfigurationReviewed} />}
          {activeSection !== "Ajustes" && state === "ready" && visibleData && !shouldShowOnboarding && <div className="space-y-5">
            {showProjection ? <Records title="Proyección" items={visibleData.projection.months}>{visibleData.projection.months.map((month) => <MoneyRecord key={month.month} record={{ description: formatMonth(month.month) }} subtitle={`Ingresos ${formatMoney(month.income)} · Gastos ${formatMoney(month.expenses)} · Ahorro ${formatMoney(month.savings_contribution)}`} amount={month.net_after_savings} />)}</Records> : <>
              <ExportCards data={visibleData} familyName={selectedFamily?.name || "Familia"} sessionUser={session.user} />
              <Records title="Cuentas" items={visibleData.accounts}>{visibleData.accounts.map((account) => <MoneyRecord key={account.id} record={{ description: account.name }} />)}</Records>
              <Records title="Categorías" items={visibleData.categories}>{visibleData.categories.map((category) => <MoneyRecord key={category.id} record={{ description: category.name }} subtitle={category.kind} />)}</Records>
              <Records title="Ingresos configurados" items={visibleData.incomeForecasts}>{visibleData.incomeForecasts.map((record) => <MoneyRecord key={record.id} record={record} subtitle={record.recurrence} />)}</Records>
              <Records title="Ingresos confirmados" items={visibleData.incomeMovements}>{visibleData.incomeMovements.map((record) => <MoneyRecord key={record.id} record={record} subtitle={formatDate(record.occurred_on)} />)}</Records>
              <Records title="Gastos configurados" items={visibleData.expenseForecasts}>{visibleData.expenseForecasts.map((record) => <MoneyRecord key={record.id} record={record} subtitle={record.recurrence} />)}</Records>
              <Records title="Gastos confirmados" items={visibleData.expenseMovements}>{visibleData.expenseMovements.map((record) => <MoneyRecord key={record.id} record={record} subtitle={formatDate(record.occurred_on)} />)}</Records>
              <Records title="Objetivos de ahorro" items={visibleData.savingsGoals}>{visibleData.savingsGoals.map((goal) => <MoneyRecord key={goal.id} record={{ description: goal.name }} subtitle={`Saldo real ${formatMoney(goal.real_balance)} · Objetivo ${formatMoney(goal.target_amount)}`} amount={goal.projected_balance} />)}</Records>
              <Records title="Movimientos de ahorro" items={visibleData.savingsMovements}>{visibleData.savingsMovements.map((record) => <MoneyRecord key={record.id} record={record} subtitle={formatDate(record.occurred_on)} />)}</Records>
              {visibleData.matiasFund && <Records title="Fondo Matías" items={[visibleData.matiasFund]}><MoneyRecord record={{ description: "Saldo real" }} subtitle={`Objetivo ${formatMoney(visibleData.matiasFund.target_amount)}`} amount={visibleData.matiasFund.real_balance} /></Records>}
            </>}
          </div>}
        </div>
      </div>

      <nav className="fixed inset-x-0 bottom-0 z-10 border-t border-slate-800 bg-slate-950/95 pb-[max(0.75rem,env(safe-area-inset-bottom))] pl-[max(1rem,env(safe-area-inset-left))] pr-[max(1rem,env(safe-area-inset-right))] pt-3 backdrop-blur" aria-label="Navegación principal">
        <div className="mx-auto grid max-w-md grid-cols-4 gap-1">
          {navigation.map((item) => (
            <button key={item.label} type="button" onClick={() => setActiveSection(item.label)} aria-current={activeSection === item.label ? "page" : undefined} className={`flex flex-col items-center gap-1 rounded-xl py-1.5 text-[11px] font-medium transition motion-reduce:transition-none ${activeSection === item.label ? "text-emerald-300" : "text-slate-500"}`}>
              <span className={`flex h-8 w-11 items-center justify-center rounded-xl ${activeSection === item.label ? "bg-emerald-400/10" : ""}`}><Icon name={item.icon} /></span>
              {item.label}
            </button>
          ))}
        </div>
      </nav>
    </main>
  );
}
