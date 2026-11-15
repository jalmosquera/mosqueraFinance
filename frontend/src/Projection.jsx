import { House, Landmark, PiggyBank, ReceiptText, Settings } from "lucide-react";
import { formatMoney } from "./formatMoney";
import { getChartData, getProjectionSummary } from "./projectionData";

const navigation = [
  { label: "Inicio", icon: House },
  { label: "Gastos", icon: ReceiptText },
  { label: "Ahorros", icon: PiggyBank },
  { label: "Ajustes", icon: Settings }
];

export function AmountDisplay({ amount, className = "" }) {
  return <output className={`amount-display ${className}`}>{formatMoney(amount) || "--"}</output>;
}

export function Progress({ value, label }) {
  const percentage = Math.max(0, Math.min(value || 0, 100));
  return <div className="projection-progress" aria-label={label}><span style={{ width: `${percentage}%` }} /></div>;
}

export function FinancialCard({ children, className = "" }) {
  return <section className={`financial-card ${className}`}>{children}</section>;
}

export function AppHeader({ familyName, username }) {
  return <header className="projection-header">
    <div className="app-brand-mark"><Landmark aria-hidden="true" /></div>
    <div className="min-w-0">
      <p className="app-brand">Mosquera <strong>Finance</strong></p>
      <h1>Proyección</h1>
      <p className="projection-family">{familyName}</p>
    </div>
    <span className="profile-mark" aria-label={`Sesión de ${username}`}>{username.slice(0, 2).toUpperCase()}</span>
  </header>;
}

export function DistributionBar({ months, contribution }) {
  const firstMonth = months[0];
  const regularContribution = firstMonth?.savings_contribution;
  return <FinancialCard className="projection-distribution">
    <div>
      <p className="eyebrow">Distribución prevista</p>
      <h2>Aportaciones a ahorro</h2>
    </div>
    <div className="distribution-row">
      <span>Acumulado de 12 meses</span>
      <AmountDisplay amount={contribution} />
    </div>
    {regularContribution !== undefined && <div className="distribution-row distribution-row-muted"><span>Primer aporte mensual previsto</span><AmountDisplay amount={regularContribution} /></div>}
  </FinancialCard>;
}

export function ProjectionChart({ months }) {
  const data = getChartData(months);
  const width = 600;
  const height = 184;
  const inset = 20;
  const max = Math.max(...data.flatMap((point) => [point.income, point.expenses, point.savings]), 1);
  const x = (index) => inset + ((width - inset * 2) * index) / Math.max(data.length - 1, 1);
  const y = (value) => height - 30 - ((height - 58) * value) / max;
  const path = (key) => data.map((point, index) => `${index ? "L" : "M"}${x(index)},${y(point[key])}`).join(" ");

  return <FinancialCard className="projection-chart-card">
    <div className="projection-chart-heading">
      <div><p className="eyebrow">Escenario de 12 meses</p><h2>Flujo mensual proyectado</h2></div>
      <div className="chart-key"><span><i className="income" />Ingresos</span><span><i className="expenses" />Gastos</span><span><i className="savings" />Ahorro</span></div>
    </div>
    {data.length ? <svg className="projection-chart" viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Gráfico de ingresos, gastos y ahorro previstos por mes">
      {[0.25, 0.5, 0.75].map((ratio) => <line key={ratio} x1={inset} x2={width - inset} y1={height - 30 - (height - 58) * ratio} y2={height - 30 - (height - 58) * ratio} />)}
      <path className="chart-line chart-income" d={path("income")} />
      <path className="chart-line chart-expenses" d={path("expenses")} />
      <path className="chart-line chart-savings" d={path("savings")} />
      {data.map((point, index) => <text key={`${point.label}-${index}`} x={x(index)} y={height - 6} textAnchor="middle">{point.label}</text>)}
    </svg> : <p className="projection-empty">No hay previsiones configuradas para proyectar.</p>}
  </FinancialCard>;
}

export function BottomNavigation({ activeSection, onSelect }) {
  return <nav className="projection-bottom-navigation" aria-label="Navegación principal"><div>{navigation.map((item) => {
    const Icon = item.icon;
    return <button key={item.label} type="button" onClick={() => onSelect(item.label)} aria-current={activeSection === item.label ? "page" : undefined} className={activeSection === item.label ? "is-active" : ""}><span className="projection-navigation-icon"><Icon aria-hidden="true" /></span>{item.label}</button>;
  })}</div></nav>;
}

export function Projection({ activeSection, familyName, onSectionChange, projection, savingsGoals, username }) {
  const summary = getProjectionSummary(projection, savingsGoals);
  return <>
    <div className="projection-page">
      <AppHeader familyName={familyName} username={username} />
      <FinancialCard className="projection-hero">
        <p className="eyebrow">Ahorro familiar estimado</p>
        <div className="projection-hero-content"><div><h2>Meta anual</h2><AmountDisplay amount={summary.target} /></div><span className="projection-percent">{summary.progress.toFixed(0)}%</span></div>
        <Progress value={summary.progress} label={`${summary.progress.toFixed(0)}% de la meta anual proyectada`} />
        <div className="projection-hero-caption"><span>Proyectado: <AmountDisplay amount={summary.projected} /></span><span>Meta: <AmountDisplay amount={summary.target} /></span></div>
      </FinancialCard>
      <div className="projection-stat-grid">
        <FinancialCard><p className="eyebrow">Ahorro real confirmado</p><AmountDisplay amount={summary.real} /><p className="real-note">Solo movimientos confirmados</p></FinancialCard>
        <FinancialCard><p className="eyebrow">Saldo al final del escenario</p><AmountDisplay amount={summary.projected} /><p className="projected-note">Estimación, no saldo real</p></FinancialCard>
      </div>
      <ProjectionChart months={summary.months} />
      <DistributionBar months={summary.months} contribution={summary.projectedContribution} />
      <p className="projection-disclaimer">Las cifras proyectadas se basan en pronósticos. Los saldos reales solo cambian con movimientos confirmados.</p>
    </div>
    <BottomNavigation activeSection={activeSection} onSelect={onSectionChange} />
  </>;
}
