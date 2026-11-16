import { Bell, CalendarDays, ChartNoAxesCombined, CircleUserRound, House, PiggyBank, ReceiptText, Settings, UsersRound, Wallet } from "lucide-react";
import { Area, AreaChart, CartesianGrid, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { formatMoney } from "./formatMoney";

const navigation = [
  { label: "Inicio", icon: House },
  { label: "Gastos", icon: ReceiptText },
  { label: "Ahorros", icon: PiggyBank },
  { label: "Ajustes", icon: Settings }
];

const chartColors = {
  accent: "#ffb11b",
  grid: "rgba(255, 255, 255, 0.14)",
  text: "var(--mf-color-text-muted)"
};

export function AmountDisplay({ amount, className = "" }) {
  return <output className={`amount-display ${className}`}>{formatMoney(amount) || "--"}</output>;
}

function formatPercentage(percentage) {
  if (typeof percentage !== "string" && typeof percentage !== "number") return "--";
  const value = String(percentage);
  return /^-?\d+(\.\d+)?$/.test(value) ? `${value.replace(".", ",")} %` : "--";
}

export function FinancialCard({ children, className = "" }) {
  return <section className={`financial-card ${className}`}>{children}</section>;
}

function AppHeader({ familyName }) {
  return <header className="projection-header">
    <div className="app-brand-mark"><Wallet aria-hidden="true" /></div>
    <div className="min-w-0">
      <p className="app-brand">Mosquera <strong>Finance</strong></p>
      <h1>{familyName}</h1>
      <p className="projection-family">Plan familiar · Proyección anual</p>
    </div>
    <span className="projection-notifications" aria-label="Notificaciones"><Bell aria-hidden="true" /></span>
  </header>;
}

function ProjectionSidebar({ activeSection, familyName, onSectionChange }) {
  return <aside className="projection-sidebar" aria-label="Navegación principal">
    <div className="projection-sidebar-brand">
      <div className="app-brand-mark"><Wallet aria-hidden="true" /></div>
      <div><p className="app-brand">Mosquera <strong>Finance</strong></p><p>{familyName}</p></div>
    </div>
    <nav className="projection-sidebar-navigation" aria-label="Secciones">
      {navigation.map((item) => {
        const Icon = item.icon;
        return <button aria-current={activeSection === item.label ? "page" : undefined} className={activeSection === item.label ? "is-active" : ""} key={item.label} onClick={() => onSectionChange(item.label)} type="button"><Icon aria-hidden="true" />{item.label}</button>;
      })}
    </nav>
    <div className="projection-sidebar-tools">
      <span aria-label="Notificaciones" className="projection-sidebar-notifications"><Bell aria-hidden="true" /></span>
      <button aria-label="Abrir ajustes de perfil" className="projection-sidebar-profile" onClick={() => onSectionChange("Ajustes")} type="button"><CircleUserRound aria-hidden="true" /><span>Perfil y ajustes</span></button>
    </div>
  </aside>;
}

function ProjectionTabs({ activeTab, onTabChange }) {
  return <div className="projection-tabs" aria-label="Vista financiera">
    {["Resumen", "Detalle", "Proyección"].map((tab) => <button aria-current={activeTab === tab ? "page" : undefined} className={activeTab === tab ? "is-active" : ""} key={tab} onClick={() => onTabChange(tab)} type="button">{tab}</button>)}
  </div>;
}

function SavingsRows({ personalSavings, familySavings }) {
  const rows = [...personalSavings, familySavings].filter(Boolean);
  return <FinancialCard className="projection-savings">
    <div><p className="eyebrow">Ahorro confirmado</p><h2>Progreso de ahorro</h2></div>
    <div className="savings-rows">
      {rows.map((saving) => {
        const IdentityIcon = saving.owner_id ? CircleUserRound : UsersRound;
        return <article className="saving-row" key={`${saving.label}-${saving.owner_id || "family"}`}>
          <IdentityIcon aria-hidden="true" className="saving-identity" />
          <div className="saving-details"><h3>{saving.label}</h3><p>Saldo real confirmado <AmountDisplay amount={saving.real_confirmed_balance} /></p><p>Objetivo anual <AmountDisplay amount={saving.annual_target} /></p><div aria-label={`Progreso de ${saving.label}: ${formatPercentage(saving.progress_percent)}`} className="saving-progress"><span style={{ "--mf-progress": `${saving.progress_percent}%` }} /></div></div>
          <strong className="saving-percentage">{formatPercentage(saving.progress_percent)}</strong>
        </article>;
      })}
    </div>
  </FinancialCard>;
}

function ProjectionChart({ chart }) {
  if (!chart.length) return null;
  return <FinancialCard className="projection-chart-card">
    <div className="projection-chart-heading"><div><p className="eyebrow">Ahorro estimado</p><h2>Proyección acumulada anual</h2></div><ChartNoAxesCombined aria-hidden="true" /></div>
    <div className="projection-chart-wrap">
      <ResponsiveContainer height="100%" width="100%">
        <AreaChart data={chart} margin={{ top: 12, right: 4, bottom: 0, left: 4 }} title="Ahorro proyectado acumulado durante 12 meses">
          <defs><linearGradient id="projected-savings-gradient" x1="0" x2="0" y1="0" y2="1"><stop offset="0%" stopColor={chartColors.accent} stopOpacity={0.52} /><stop offset="100%" stopColor={chartColors.accent} stopOpacity={0.02} /></linearGradient></defs>
          <CartesianGrid stroke={chartColors.grid} strokeDasharray="3 5" vertical={false} />
          <XAxis axisLine={false} dataKey="label" interval="preserveStartEnd" tick={{ fill: chartColors.text, fontSize: 11 }} tickLine={false} />
          <YAxis axisLine={false} dataKey="cumulative_projected_savings" tick={{ fill: chartColors.text, fontSize: 11 }} tickFormatter={(value) => formatMoney(String(value))} tickLine={false} width={72} />
          <Tooltip contentStyle={{ background: "#111", border: "1px solid rgba(255,255,255,.25)", borderRadius: "12px" }} formatter={(value) => [formatMoney(String(value)), "Ahorro acumulado"]} labelFormatter={(label) => `Mes: ${label}`} />
          <Area dataKey="cumulative_projected_savings" dot={false} fill="url(#projected-savings-gradient)" name="Ahorro acumulado" stroke="none" type="monotone" />
          <Line dataKey="cumulative_projected_savings" dot={{ fill: chartColors.accent, r: 3, stroke: "#111", strokeWidth: 2 }} isAnimationActive={false} stroke={chartColors.accent} strokeLinecap="round" strokeLinejoin="round" strokeOpacity={1} strokeWidth={4.5} type="monotone" />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  </FinancialCard>;
}

function MonthlyForecasts({ chart, summary }) {
  const [firstMonth, ...laterMonths] = chart;
  const repeatedMonthlyAmount = summary?.subsequent_month_projected_savings || laterMonths[0]?.projected_savings;
  if (!firstMonth) return null;
  return <div className="projection-months">
    <FinancialCard className="projection-month-card projection-month-card--first"><CalendarDays aria-hidden="true" /><p className="eyebrow">Mes 1 · {firstMonth.label}</p><h2>Ahorro previsto</h2><AmountDisplay amount={firstMonth.projected_savings} /><p>Importe autorizado para este mes</p></FinancialCard>
    <FinancialCard className="projection-month-card"><CalendarDays aria-hidden="true" /><p className="eyebrow">Meses 2-12</p><h2>Previsión mensual autorizada</h2><AmountDisplay amount={repeatedMonthlyAmount} /><p>Importe mensual repetido autorizado por el servidor.</p></FinancialCard>
  </div>;
}

function Distribution({ distribution, chart, familySavings }) {
  if (!distribution || !chart.length) return null;
  const percentages = [distribution.first_owner_percentage, distribution.second_owner_percentage, distribution.family_percentage].map(formatPercentage);
  const laterMonth = chart[1];
  return <FinancialCard className="projection-distribution">
    <div><p className="eyebrow">Distribución prevista</p><h2>{percentages.join(" / ")}</h2></div>
    <div className="distribution-segments" aria-label="Distribución autorizada del ahorro" style={{ gridTemplateColumns: `${distribution.first_owner_percentage}fr ${distribution.second_owner_percentage}fr ${distribution.family_percentage}fr` }}><span>{percentages[0]}</span><span>{percentages[1]}</span><span>{percentages[2]}</span></div>
    {laterMonth && <><p className="distribution-caption">Importes autorizados por mes desde {laterMonth.label}.</p><div className="distribution-months"><div><span>{distribution.first_owner.label}</span><AmountDisplay amount={laterMonth.first_owner_amount} /></div><div><span>{distribution.second_owner.label}</span><AmountDisplay amount={laterMonth.second_owner_amount} /></div><div><span>{familySavings.label}</span><AmountDisplay amount={laterMonth.family_amount} /></div></div></>}
  </FinancialCard>;
}

function MatiasPlan({ plan }) {
  if (!plan) return null;
  return <FinancialCard className="matias-plan">
    <p className="eyebrow">Plan independiente</p><h2>Fondo Matías</h2>
    <div className="matias-amounts"><span>Saldo real confirmado <AmountDisplay amount={plan.real_confirmed_balance} /></span><span>Objetivo <AmountDisplay amount={plan.target_amount} /></span><span>Inicial por progenitor <AmountDisplay amount={plan.initialContributionPerParent} /></span><span>Inicial total <AmountDisplay amount={plan.initial_contribution_total} /></span><span>Gasto mensual simulado <AmountDisplay amount={plan.monthly_simulated_expenditure} /></span><span>Posterior por progenitor / total <AmountDisplay amount={plan.monthlyReplenishmentPerParent} /> / <AmountDisplay amount={plan.monthly_replenishment_total} /></span></div>
    <p>Los aportes y reposiciones del fondo no forman parte del ahorro familiar ni son un segundo gasto de consumo.</p>
    <span className="matias-label">Gestionable desde Ahorros</span>
  </FinancialCard>;
}

function FreeMoney({ allowance }) {
  if (!allowance) return null;
  const [firstAmount] = allowance.monthly_amounts;
  const hasRepeatedAmount = allowance.monthly_amounts.every((amount) => amount === firstAmount);
  return <FinancialCard className="free-money-card">
    <div><p className="eyebrow">Disponible personal</p><h2>Dinero libre</h2></div>
    <Wallet aria-hidden="true" />
    {hasRepeatedAmount ? <p className="free-money-repeated"><AmountDisplay amount={firstAmount} /> cada uno</p> : <div className="free-money-amounts">{allowance.monthly_amounts.map((amount, index) => <div key={`${index}-${amount}`}><span>{index === 0 ? "Mes 1" : `Mes ${index + 1}`}</span><AmountDisplay amount={amount} /></div>)}</div>}
  </FinancialCard>;
}

function ProjectionStatus({ projectionState }) {
  if (projectionState.status === "loading" || projectionState.status === "idle") return <FinancialCard className="projection-status" role="status"><p>Cargando pronóstico aprobado…</p></FinancialCard>;
  if (projectionState.status === "configuration") return <FinancialCard className="projection-status" role="alert"><p className="eyebrow">Configuración necesaria</p><h2>Faltan previsiones aprobadas</h2><p>La proyección anual se mostrará cuando estén configurados estos meses: {projectionState.missingMonths.join(", ")}.</p></FinancialCard>;
  if (projectionState.status === "error") return <FinancialCard className="projection-status" role="alert"><p className="eyebrow">No disponible</p><h2>No se pudo cargar la proyección</h2><p>Intentá nuevamente cuando la conexión esté disponible.</p></FinancialCard>;
  return null;
}

export function BottomNavigation({ activeSection, onSelect }) {
  return <nav className="projection-bottom-navigation" aria-label="Navegación principal"><div>{navigation.map((item) => {
    const Icon = item.icon;
    return <button key={item.label} type="button" onClick={() => onSelect(item.label)} aria-current={activeSection === item.label ? "page" : undefined} className={activeSection === item.label ? "is-active" : ""}><span className="projection-navigation-icon"><Icon aria-hidden="true" /></span>{item.label}</button>;
  })}</div></nav>;
}

export function Projection({ activeSection, activeTab, familyName, onSectionChange, onTabChange, projectionState }) {
  const projection = projectionState.data;
  const isMember = projection?.role === "MEMBER";
  return <div className="projection-dashboard">
    <ProjectionSidebar activeSection={activeSection} familyName={familyName} onSectionChange={onSectionChange} />
    <div className="projection-page">
      <AppHeader familyName={familyName} />
      <ProjectionTabs activeTab={activeTab} onTabChange={onTabChange} />
      {projectionState.status !== "ready" ? <ProjectionStatus projectionState={projectionState} /> : <>
        {isMember ? <FinancialCard className="projection-privacy"><p className="eyebrow">Datos autorizados</p><h2>Tu vista privada</h2><p>La proyección anual y los datos privados de Jalberth no están disponibles para tu perfil.</p></FinancialCard> : <>
          <FinancialCard className="projection-hero"><p className="eyebrow">Proyección anual aprobada</p><h2>Ahorro previsto en 12 meses</h2><AmountDisplay amount={projection.summary?.annual_projected_savings} /><p>Estimación de planificación, no saldo real confirmado.</p></FinancialCard>
          <ProjectionChart chart={projection.chart} />
        </>}
        <SavingsRows familySavings={projection.familySavings} personalSavings={projection.personalSavings} />
        {!isMember && <MonthlyForecasts chart={projection.chart} summary={projection.summary} />}
        {!isMember && <Distribution chart={projection.chart} distribution={projection.distribution} familySavings={projection.familySavings} />}
        <MatiasPlan plan={projection.matiasPlan} />
        <FreeMoney allowance={projection.freeMoney} />
      </>}
    </div>
    <BottomNavigation activeSection={activeSection} onSelect={onSectionChange} />
  </div>;
}
