import { useEffect, useState } from "react";
import { Coins, CreditCard, House, Plus, Settings as SettingsIcon } from "lucide-react";
import { bootstrapSession, getApprovedForecast, getExpenseDashboard, getFamilies, getFamilyData, getMemberships, isForbidden, isUnauthenticated, login, logout } from "./api";
import { ExpensesDashboard } from "./ExpensesDashboard.jsx";
import { createExportImage, downloadImage } from "./exportImage";
import { createExportPayload } from "./exportPayload";
import { formatDate } from "./formatDate";
import { formatMoney } from "./formatMoney";
import { Projection } from "./Projection";
import { mapApprovedForecast } from "./projectionData";
import { Settings } from "./Settings";

export { formatMoney };

const tabs = ["Resumen", "Detalle", "Proyección"];
const navigation = [
  { label: "Inicio", icon: House },
  { label: "Gastos", icon: CreditCard },
  { label: "Ahorros", icon: Coins },
  { label: "Ajustes", icon: SettingsIcon }
];

function EmptyState({ children }) {

  return (
    <section className="mf-card mf-card--flat mf-empty-state">
      <div className="mf-icon-tile">
        <svg viewBox="0 0 24 24" className="h-6 w-6" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="1.7"><path d="M12 3v18M3 12h18" strokeLinecap="round" /></svg>
      </div>
      <h2>Todos los datos están al día</h2>
      <p>{children}</p>
    </section>
  );
}

function Records({ title, items, children }) {
  return (
    <section className="mf-card mf-records">
      <div className="flex items-center justify-between gap-3">
        <h2>{title}</h2>
        <span className="mf-badge">{items.length}</span>
      </div>
      {items.length ? <div className="mf-record-list">{children}</div> : <p className="mf-panel-empty">Aún no se configuró información.</p>}
    </section>
  );
}

function MoneyRecord({ record, subtitle, amount = record.amount }) {
  return (
    <article className="mf-record-row">
      <div className="min-w-0">
        <p>{record.description || "Sin descripción"}</p>
        {subtitle && <p>{subtitle}</p>}
      </div>
      {amount !== undefined && <p className="mf-record-amount">{formatMoney(amount)}</p>}
    </article>
  );
}

function NavigationButton({ activeSection, item, onSelect }) {
  const Icon = item.icon;
  return <button type="button" onClick={() => onSelect(item.label)} aria-current={activeSection === item.label ? "page" : undefined}>
    <span><Icon aria-hidden="true" /></span>
    {item.label}
  </button>;
}

function QuickAdd({ onSelect }) {
  const [open, setOpen] = useState(false);
  function select(type) {
    setOpen(false);
    onSelect(type);
  }
  return <div className="quick-add">
    {open && <div className="quick-add-menu" role="dialog" aria-label="Añadir movimiento">
      <button onClick={() => select("income")} type="button">Añadir ingreso</button>
      <button onClick={() => select("expense")} type="button">Añadir gasto</button>
    </div>}
    <button aria-expanded={open} aria-label="Añadir movimiento" className="quick-add-button" onClick={() => setOpen((current) => !current)} type="button"><Plus aria-hidden="true" /></button>
  </div>;
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
    <main className="mf-login-page">
      <section className="mf-card mf-login-card">
        <div className="app-brand-mark">MF</div>
        <p className="mf-eyebrow">Mosquera Finance</p>
        <h1 className="mf-title">Tu espacio familiar</h1>
        <p className="mf-muted">Ingresá para consultar la información que tenés autorizada.</p>
        <form className="mf-form" onSubmit={submit}>
          <label className="mf-field mf-label">Usuario<input autoComplete="username" className="mf-input" onChange={(event) => setUsername(event.target.value)} required value={username} /></label>
          <label className="mf-field mf-label">Contraseña<input autoComplete="current-password" className="mf-input" onChange={(event) => setPassword(event.target.value)} required type="password" value={password} /></label>
          {status === "error" && <p className="mf-message mf-message--error" role="alert">No se pudo iniciar sesión. Verificá tus datos e intentá nuevamente.</p>}
          <button aria-busy={status === "submitting"} className="mf-button mf-button--block" disabled={status === "submitting"} type="submit">{status === "submitting" ? "Ingresando..." : "Iniciar sesión"}</button>
        </form>
        <p className="mt-5 text-center text-xs leading-5 text-slate-500">Tu sesión se mantiene protegida en este dispositivo.</p>
      </section>
    </main>
  );
}

function FirstRunOnboarding({ isAdmin, onConfigure, reviewed, setReviewed }) {
  if (!isAdmin) {
    return (
      <section className="mf-card mf-panel mf-panel--notice" role="status">
        <p className="mf-eyebrow">Acceso limitado</p>
        <h2>La configuración inicial la administra Jalberth</h2>
        <p>Vas a ver únicamente los datos compartidos y los tuyos que estén autorizados. Los ingresos, gastos, ahorros, proyecciones y exportaciones privados de Jalberth no se muestran en tu cuenta.</p>
      </section>
    );
  }

  return (
    <section className="mf-card mf-card--accent mf-onboarding">
      <p className="mf-eyebrow">Configuración inicial</p>
      <h2>Primero definí el plan, después registrá lo real</h2>
      <div>
        <p>Los pronósticos describen importes previstos y sirven para planificar. No son movimientos confirmados ni modifican los saldos reales.</p>
        <p>Los movimientos reales se registran cuando ocurren. Conservan su historial y se corrigen con operaciones auditadas, no eliminándolos.</p>
      </div>
      <label className="mf-check-card">
        <input checked={reviewed} onChange={(event) => setReviewed(event.target.checked)} type="checkbox" />
        <span>Revisé la diferencia entre pronósticos y movimientos reales. Confirmo que voy a verificar la información antes de guardarla.</span>
      </label>
      <button className="mf-button mf-button--block" disabled={!reviewed} onClick={onConfigure} type="button">Ir a la configuración inicial</button>
      <p className="mf-note mf-onboarding-note">La configuración inicial crea solo datos de planificación; los movimientos reales se registran por separado.</p>
    </section>
  );
}

function ExportCards({ data, familyName, sessionUser }) {
  const [recipient, setRecipient] = useState("Raiza");
  const [status, setStatus] = useState("idle");
  const [error, setError] = useState("");
  const recipientCopy = {
    Raiza: "Vista de Raiza: gastos compartidos y sus datos personales autorizados. Nunca incluye información privada de Jalberth.",
    Jalberth: "Vista de Jalberth: gastos compartidos y sus datos personales autorizados.",
    both: "Se crearán dos PNG independientes, uno para cada destinatario con sus permisos aplicados."
  };

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
    <section className="mf-card mf-panel">
      <h2>Compartir resumen privado</h2>
      <p>Se crea una tarjeta PNG por destinatario. La tarjeta de Raiza solo incluye datos compartidos y sus propios datos autorizados.</p>
      <fieldset className="mt-4 grid grid-cols-3 gap-2" disabled={status === "loading"}>
        <legend className="sr-only">Destinatario</legend>
        {[{ value: "Raiza", label: "Raiza" }, { value: "Jalberth", label: "Jalberth" }, { value: "both", label: "Ambos" }].map((option) => <label key={option.value} className={`export-recipient-option ${recipient === option.value ? "is-active" : ""}`}><input checked={recipient === option.value} className="sr-only" name="export-recipient" onChange={() => setRecipient(option.value)} type="radio" value={option.value} />{option.label}</label>)}
      </fieldset>
      <p className="export-recipient-preview" role="status">{recipientCopy[recipient]}</p>
      {error && <p className="mt-3 text-sm text-rose-200" role="alert">{error}</p>}
      {status === "shared" && <p className="mt-3 text-sm text-emerald-200" role="status">Tarjeta compartida.</p>}
      {status === "downloaded" && <p className="mt-3 text-sm text-emerald-200" role="status">La descarga empezó porque compartir archivos no está disponible.</p>}
      <button aria-busy={status === "loading"} type="button" onClick={exportCards} disabled={status === "loading"} className="mf-button mf-button--block mt-5">{status === "loading" ? "Generando tarjetas..." : `Generar resumen para ${recipient === "both" ? "ambos" : recipient}`}</button>
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
  const [projectionState, setProjectionState] = useState({ status: "idle", data: null, missingMonths: [] });
  const [expenseDashboardState, setExpenseDashboardState] = useState({ status: "idle", data: null });
  const [expenseMonth, setExpenseMonth] = useState(() => new Date().toISOString().slice(0, 7));
  const [settingsPanel, setSettingsPanel] = useState("profile");
  const [expenseCreationRequest, setExpenseCreationRequest] = useState(0);
  const [incomeCreationRequest, setIncomeCreationRequest] = useState(0);

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
    getFamilyData(familyId, controller.signal)
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
  const showProjection = activeSection === "Inicio" && activeTab === "Proyección";
  const showExpenses = activeSection === "Gastos";
  const visibleData = loadedFamilyId === familyId ? data : null;
  const currentMembership = memberships.find((membership) => membership.user_id === session.user?.id && membership.is_active);
  const isAdmin = currentMembership?.role === "ADMIN";
  const isFirstRun = Boolean(visibleData) && !visibleData.accounts.length && !visibleData.categories.length && !visibleData.incomeForecasts.length && !visibleData.expenseForecasts.length;
  const shouldShowOnboarding = activeSection === "Inicio" && state === "ready" && visibleData && membershipsLoadedFor === familyId && isFirstRun && !initialConfigurationReviewed;

  useEffect(() => {
    if (session.status !== "authenticated" || !familyId || !showProjection) {
      setProjectionState({ status: "idle", data: null, missingMonths: [] });
      return undefined;
    }

    const controller = new AbortController();
    setProjectionState({ status: "loading", data: null, missingMonths: [] });
    getApprovedForecast(familyId, firstDayOfCurrentMonth(), controller.signal)
      .then((response) => setProjectionState({
        status: "ready",
        data: mapApprovedForecast(response, { currentUserId: session.user?.id, memberships }),
        missingMonths: []
      }))
      .catch((error) => {
        if (error.code === "ERR_CANCELED") return;
        const missingMonths = error.response?.data?.missing_budget_months;
        setProjectionState({
          status: Array.isArray(missingMonths) ? "configuration" : "error",
          data: null,
          missingMonths: missingMonths || []
        });
      });
    return () => controller.abort();
  }, [familyId, memberships, reloadKey, session.status, session.user?.id, showProjection]);

  useEffect(() => {
    if (session.status !== "authenticated" || !familyId || !showExpenses) {
      setExpenseDashboardState({ status: "idle", data: null });
      return undefined;
    }
    const controller = new AbortController();
    setExpenseDashboardState({ status: "loading", data: null });
    getExpenseDashboard(familyId, expenseMonth, controller.signal)
      .then((response) => setExpenseDashboardState({ status: "ready", data: response }))
      .catch((error) => {
        if (error.code !== "ERR_CANCELED") setExpenseDashboardState({ status: "error", data: null });
      });
    return () => controller.abort();
  }, [expenseMonth, familyId, reloadKey, session.status, showExpenses]);

  function openExpenseMovements(create = false) {
    setSettingsPanel("movements");
    if (create) setExpenseCreationRequest((current) => current + 1);
    setActiveSection("Ajustes");
  }

  function openQuickAdd(type) {
    setSettingsPanel("movements");
    if (type === "income") setIncomeCreationRequest((current) => current + 1);
    else setExpenseCreationRequest((current) => current + 1);
    setActiveSection("Ajustes");
  }

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
    <main className="mf-page mf-app-shell">
      <div className={`mf-app-content ${showProjection && activeSection === "Inicio" ? "max-w-6xl projection-shell" : showExpenses ? "max-w-6xl expenses-shell" : "max-w-md"}`}>
        {!showProjection && !showExpenses && <header className="mf-app-header">
          <div>
            <p className="mf-eyebrow">Mosquera Finance</p>
            <h1 className="mf-title">{selectedFamily?.name || activeSection}</h1>
          </div>
          <button className="mf-avatar" onClick={signOut} type="button" aria-label="Cerrar sesión">{session.user.username.slice(0, 2).toUpperCase()}</button>
        </header>}

        {families.length > 1 && activeSection !== "Ajustes" && <label className="mf-field mf-family-select">Familia<select value={familyId} onChange={(event) => setFamilyId(event.target.value)} className="mf-input">{families.map((family) => <option key={family.id} value={family.id}>{family.name}</option>)}</select></label>}

        {activeSection !== "Ajustes" && !showProjection && !showExpenses && <div className="mf-segmented" aria-label="Vista financiera">
          {tabs.map((tab) => (
            <button
              key={tab}
              type="button"
              onClick={() => setActiveTab(tab)}
              className={activeTab === tab ? "is-active" : ""}
            >
              {tab}
            </button>
          ))}
        </div>}

        <div className="mt-6">
          {activeSection === "Ajustes" && shouldShowOnboarding && <FirstRunOnboarding isAdmin={isAdmin} onConfigure={openInitialConfiguration} reviewed={initialConfigurationReviewed} setReviewed={setInitialConfigurationReviewed} />}
          {activeSection === "Ajustes" && familyId && !shouldShowOnboarding && <Settings accounts={visibleData?.accounts || []} categories={visibleData?.categories || []} data={visibleData} expenseCreationRequest={expenseCreationRequest} expenseForecasts={visibleData?.expenseForecasts || []} families={families} familyId={familyId} incomeCreationRequest={incomeCreationRequest} incomeForecasts={visibleData?.incomeForecasts || []} initialPanel={settingsPanel} isAdmin={isAdmin} onChanged={reloadFamilyData} onFamilyChange={setFamilyId} onLogout={signOut} sessionUser={session.user} />}
          {showExpenses && familyId && <ExpensesDashboard dashboard={expenseDashboardState.data} month={expenseMonth} onAddExpense={() => openExpenseMovements(true)} onMonthChange={setExpenseMonth} onRetry={reloadFamilyData} onViewMovements={() => openExpenseMovements()} status={expenseDashboardState.status} />}
          {activeSection !== "Ajustes" && !showExpenses && state === "loading" && <section className="rounded-[2rem] border border-slate-900 bg-slate-900/40 p-5" aria-live="polite" role="status"><p className="text-sm font-medium text-slate-300">Cargando información protegida</p><div className="mt-4 space-y-3" aria-hidden="true"><div className="h-3 w-2/5 animate-pulse motion-reduce:animate-none rounded-full bg-slate-800" /><div className="h-3 w-full animate-pulse motion-reduce:animate-none rounded-full bg-slate-800" /></div></section>}
          {activeSection !== "Ajustes" && !showExpenses && state === "unauthenticated" && <EmptyState>Tu sesión no está disponible. Iniciá sesión para consultar la información autorizada.</EmptyState>}
          {activeSection !== "Ajustes" && !showExpenses && state === "forbidden" && <section className="rounded-[2rem] border border-amber-900/60 bg-amber-950/20 p-6" role="alert"><h2 className="text-lg font-semibold text-white">No tenés acceso a esta información</h2><p className="mt-2 text-sm leading-6 text-slate-400">Por privacidad, no mostramos detalles de datos que no están autorizados para tu perfil.</p><button type="button" onClick={retry} className="mt-5 rounded-xl bg-amber-300 px-4 py-2 text-sm font-semibold text-slate-950">Reintentar</button></section>}
          {activeSection !== "Ajustes" && !showExpenses && state === "error" && <section className="rounded-[2rem] border border-rose-900/60 bg-rose-950/30 p-6" role="alert"><h2 className="text-lg font-semibold text-white">No se pudo cargar la información</h2><p className="mt-2 text-sm leading-6 text-slate-400">Verificá la conexión e intentá nuevamente.</p><button type="button" onClick={retry} className="mt-5 rounded-xl bg-rose-300 px-4 py-2 text-sm font-semibold text-slate-950">Reintentar</button></section>}
          {activeSection !== "Ajustes" && !showExpenses && state === "empty" && <EmptyState>No tenés una familia autorizada para consultar.</EmptyState>}
          {activeSection !== "Ajustes" && !showExpenses && shouldShowOnboarding && <FirstRunOnboarding isAdmin={isAdmin} onConfigure={openInitialConfiguration} reviewed={initialConfigurationReviewed} setReviewed={setInitialConfigurationReviewed} />}
          {activeSection !== "Ajustes" && !showExpenses && state === "ready" && visibleData && !shouldShowOnboarding && <div className="space-y-5">
            {showProjection ? <Projection activeSection={activeSection} activeTab={activeTab} familyName={selectedFamily?.name || "Familia"} onSectionChange={setActiveSection} onTabChange={setActiveTab} projectionState={projectionState} /> : <>
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

      {!showProjection && <nav className={`app-bottom-navigation mf-bottom-bar ${showExpenses ? "expenses-bottom-navigation" : ""}`} aria-label="Navegación principal">
        <div>
          {navigation.map((item) => (
            <NavigationButton activeSection={activeSection} item={item} key={item.label} onSelect={setActiveSection} />
          ))}
        </div>
      </nav>}
      {activeSection === "Inicio" && !showProjection && state === "ready" && <QuickAdd onSelect={openQuickAdd} />}
    </main>
  );
}
