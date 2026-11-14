import { useEffect, useState } from "react";
import { getFamilies, getFamilyData, isUnauthenticated } from "./api";

export function formatMoney(amount) {
  if (typeof amount !== "string" && typeof amount !== "number") {
    return null;
  }

  const value = String(amount);
  if (!/^-?\d+(\.\d{1,2})?$/.test(value)) {
    return null;
  }

  const negative = value.startsWith("-");
  const [integer, decimal = ""] = (negative ? value.slice(1) : value).split(".");
  const groupedInteger = integer.replace(/\B(?=(\d{3})+(?!\d))/g, ".");
  return `${negative ? "-" : ""}${groupedInteger},${decimal.padEnd(2, "0")} €`;
}

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

export function App() {
  const [activeTab, setActiveTab] = useState("Resumen");
  const [activeSection, setActiveSection] = useState("Inicio");
  const [families, setFamilies] = useState([]);
  const [familyId, setFamilyId] = useState("");
  const [data, setData] = useState(null);
  const [state, setState] = useState("loading");

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
          setState(isUnauthenticated(error) ? "unauthenticated" : "error");
        }
      });
    return () => controller.abort();
  }

  function retry() {
    setData(null);
    setFamilyId("");
    loadFamilies();
  }

  useEffect(() => loadFamilies(), []);

  useEffect(() => {
    if (!familyId) {
      return undefined;
    }

    const controller = new AbortController();
    setData(null);
    setState("loading");
    getFamilyData(familyId, firstDayOfCurrentMonth(), controller.signal)
      .then((response) => {
        setData(response);
        setState("ready");
      })
      .catch((error) => {
        if (error.code !== "ERR_CANCELED") {
          setState(isUnauthenticated(error) ? "unauthenticated" : "error");
        }
      });
    return () => controller.abort();
  }, [familyId]);

  const selectedFamily = families.find((family) => String(family.id) === familyId);
  const showProjection = activeTab === "Proyección";

  return (
    <main className="min-h-dvh bg-slate-950 text-slate-100">
      <div className="mx-auto flex min-h-dvh max-w-md flex-col px-5 pb-28 pt-[max(1.5rem,env(safe-area-inset-top))]">
        <header className="flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-emerald-300">Mosquera Finance</p>
            <h1 className="mt-2 text-3xl font-semibold tracking-tight text-white">{selectedFamily?.name || activeSection}</h1>
          </div>
          <div className="flex h-11 w-11 items-center justify-center rounded-full border border-slate-800 bg-slate-900 text-sm font-semibold text-slate-300" aria-label="Sesión protegida">MF</div>
        </header>

        {families.length > 1 && <label className="mt-6 block text-sm text-slate-400">Familia<select value={familyId} onChange={(event) => setFamilyId(event.target.value)} className="mt-2 block w-full rounded-xl border border-slate-800 bg-slate-900 px-3 py-3 text-sm font-medium text-white">{families.map((family) => <option key={family.id} value={family.id}>{family.name}</option>)}</select></label>}

        <div className="mt-8 flex rounded-2xl bg-slate-900 p-1" role="tablist" aria-label="Vista financiera">
          {tabs.map((tab) => (
            <button
              key={tab}
              type="button"
              role="tab"
              aria-selected={activeTab === tab}
              onClick={() => setActiveTab(tab)}
              className={`flex-1 rounded-xl px-2 py-2.5 text-xs font-semibold transition ${activeTab === tab ? "bg-slate-700 text-white shadow-sm" : "text-slate-500"}`}
            >
              {tab}
            </button>
          ))}
        </div>

        <div className="mt-6">
          {state === "loading" && <section className="rounded-[2rem] border border-slate-900 bg-slate-900/40 p-5" aria-label="Cargando datos"><p className="text-sm font-medium text-slate-300">Cargando información protegida</p><div className="mt-4 space-y-3" aria-hidden="true"><div className="h-3 w-2/5 animate-pulse rounded-full bg-slate-800" /><div className="h-3 w-full animate-pulse rounded-full bg-slate-800" /></div></section>}
          {state === "unauthenticated" && <EmptyState>Tu sesión no está disponible. Iniciá sesión para consultar la información autorizada.</EmptyState>}
          {state === "error" && <section className="rounded-[2rem] border border-rose-900/60 bg-rose-950/30 p-6"><h2 className="text-lg font-semibold text-white">No se pudo cargar la información</h2><p className="mt-2 text-sm leading-6 text-slate-400">Verificá la conexión e intentá nuevamente.</p><button type="button" onClick={retry} className="mt-5 rounded-xl bg-rose-300 px-4 py-2 text-sm font-semibold text-slate-950">Reintentar</button></section>}
          {state === "empty" && <EmptyState>No tenés una familia autorizada para consultar.</EmptyState>}
          {state === "ready" && data && <div className="space-y-5">
            {showProjection ? <Records title="Proyección" items={data.projection.months}>{data.projection.months.map((month) => <MoneyRecord key={month.month} record={{ description: month.month }} subtitle={`Ingresos ${formatMoney(month.income)} · Gastos ${formatMoney(month.expenses)} · Ahorro ${formatMoney(month.savings_contribution)}`} amount={month.net_after_savings} />)}</Records> : <>
              <Records title="Cuentas" items={data.accounts}>{data.accounts.map((account) => <MoneyRecord key={account.id} record={{ description: account.name }} />)}</Records>
              <Records title="Categorías" items={data.categories}>{data.categories.map((category) => <MoneyRecord key={category.id} record={{ description: category.name }} subtitle={category.kind} />)}</Records>
              <Records title="Ingresos configurados" items={data.incomeForecasts}>{data.incomeForecasts.map((record) => <MoneyRecord key={record.id} record={record} subtitle={record.recurrence} />)}</Records>
              <Records title="Ingresos confirmados" items={data.incomeMovements}>{data.incomeMovements.map((record) => <MoneyRecord key={record.id} record={record} subtitle={record.occurred_on} />)}</Records>
              <Records title="Gastos configurados" items={data.expenseForecasts}>{data.expenseForecasts.map((record) => <MoneyRecord key={record.id} record={record} subtitle={record.recurrence} />)}</Records>
              <Records title="Gastos confirmados" items={data.expenseMovements}>{data.expenseMovements.map((record) => <MoneyRecord key={record.id} record={record} subtitle={record.occurred_on} />)}</Records>
              <Records title="Objetivos de ahorro" items={data.savingsGoals}>{data.savingsGoals.map((goal) => <MoneyRecord key={goal.id} record={{ description: goal.name }} subtitle={`Saldo real ${formatMoney(goal.real_balance)} · Objetivo ${formatMoney(goal.target_amount)}`} amount={goal.projected_balance} />)}</Records>
              <Records title="Movimientos de ahorro" items={data.savingsMovements}>{data.savingsMovements.map((record) => <MoneyRecord key={record.id} record={record} subtitle={record.occurred_on} />)}</Records>
              {data.matiasFund && <Records title="Fondo Matías" items={[data.matiasFund]}><MoneyRecord record={{ description: "Saldo real" }} subtitle={`Objetivo ${formatMoney(data.matiasFund.target_amount)}`} amount={data.matiasFund.real_balance} /></Records>}
            </>}
          </div>}
        </div>
      </div>

      <nav className="fixed inset-x-0 bottom-0 z-10 border-t border-slate-800 bg-slate-950/95 px-4 pb-[max(0.75rem,env(safe-area-inset-bottom))] pt-3 backdrop-blur" aria-label="Navegación principal">
        <div className="mx-auto grid max-w-md grid-cols-4 gap-1">
          {navigation.map((item) => (
            <button key={item.label} type="button" onClick={() => setActiveSection(item.label)} className={`flex flex-col items-center gap-1 rounded-xl py-1.5 text-[11px] font-medium transition ${activeSection === item.label ? "text-emerald-300" : "text-slate-500"}`}>
              <span className={`flex h-8 w-11 items-center justify-center rounded-xl ${activeSection === item.label ? "bg-emerald-400/10" : ""}`}><Icon name={item.icon} /></span>
              {item.label}
            </button>
          ))}
        </div>
      </nav>
    </main>
  );
}
