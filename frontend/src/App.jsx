import { useState } from "react";

const moneyFormatter = new Intl.NumberFormat("es-ES", {
  style: "currency",
  currency: "EUR"
});

export function formatMoney(amount) {
  return moneyFormatter.format(amount);
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

function EmptyState({ section, tab }) {
  const message = tab === "Proyección"
    ? "Configurá los forecasts para consultar proyecciones."
    : section === "Ahorros"
      ? "Conectá datos o configurá objetivos de ahorro."
      : "Conectá datos o configurá los forecasts iniciales.";

  return (
    <section className="rounded-[2rem] border border-slate-800 bg-slate-900/70 p-6 shadow-2xl shadow-slate-950/30">
      <div className="mb-5 flex h-12 w-12 items-center justify-center rounded-2xl bg-emerald-400/10 text-emerald-300">
        <svg viewBox="0 0 24 24" className="h-6 w-6" aria-hidden="true" fill="none" stroke="currentColor" strokeWidth="1.7"><path d="M12 3v18M3 12h18" strokeLinecap="round" /></svg>
      </div>
      <h2 className="text-lg font-semibold text-white">Todavía no hay información para mostrar</h2>
      <p className="mt-2 max-w-sm text-sm leading-6 text-slate-400">{message}</p>
      <p className="mt-5 text-xs font-medium uppercase tracking-[0.16em] text-slate-500">Importes confirmados</p>
      <p className="mt-1 text-sm text-slate-400">Sin datos conectados</p>
    </section>
  );
}

export function App() {
  const [activeTab, setActiveTab] = useState("Resumen");
  const [activeSection, setActiveSection] = useState("Inicio");

  return (
    <main className="min-h-dvh bg-slate-950 text-slate-100">
      <div className="mx-auto flex min-h-dvh max-w-md flex-col px-5 pb-28 pt-[max(1.5rem,env(safe-area-inset-top))]">
        <header className="flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.2em] text-emerald-300">Mosquera Finance</p>
            <h1 className="mt-2 text-3xl font-semibold tracking-tight text-white">{activeSection}</h1>
          </div>
          <div className="flex h-11 w-11 items-center justify-center rounded-full border border-slate-800 bg-slate-900 text-sm font-semibold text-slate-300" aria-label="Perfil sin conectar">MF</div>
        </header>

        <section className="mt-8 overflow-hidden rounded-[2rem] border border-slate-800 bg-gradient-to-br from-slate-900 to-slate-950 p-6">
          <p className="text-sm text-slate-400">Visión familiar</p>
          <div className="mt-3 flex items-end justify-between gap-4">
            <div>
              <p className="text-2xl font-semibold tracking-tight text-white">Aún sin saldo confirmado</p>
              <p className="mt-2 text-sm leading-5 text-slate-400">Los movimientos aparecerán al conectar datos seguros.</p>
            </div>
            <span className="mb-1 h-2.5 w-2.5 shrink-0 rounded-full bg-amber-300" title="Pendiente de configuración" />
          </div>
        </section>

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
          <EmptyState section={activeSection} tab={activeTab} />
          <section className="mt-5 rounded-[2rem] border border-slate-900 bg-slate-900/40 p-5" aria-label="Estado de carga">
            <div className="flex items-center justify-between">
              <p className="text-sm font-medium text-slate-300">Estado de conexión</p>
              <span className="text-xs font-medium text-slate-500">Esperando datos</span>
            </div>
            <div className="mt-4 space-y-3" aria-hidden="true">
              <div className="h-3 w-2/5 animate-pulse rounded-full bg-slate-800" />
              <div className="h-3 w-full animate-pulse rounded-full bg-slate-800" />
            </div>
          </section>
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
