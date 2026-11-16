import { CalendarDays, ChevronRight, CirclePlus, Coins, Ellipsis, House, List, Scissors, ShoppingCart, UserRound, WalletCards, Zap } from "lucide-react";
import { formatDate, formatMonth } from "./formatDate";
import { formatMoney } from "./formatMoney";
import { categoryIconName, isMemberDashboard } from "./expensesDashboard";

const icons = { Ellipsis, House, Scissors, ShoppingCart, Zap, CreditCard: WalletCards };

function CategoryIcon({ name }) {
  const Icon = icons[categoryIconName(name)];
  return <Icon aria-hidden="true" />;
}

function MonthPicker({ month, onChange }) {
  return <label className="expenses-month-picker">
    <CalendarDays aria-hidden="true" />
    <span>{formatMonth(month)}</span>
    <input aria-label="Mes de gastos" onChange={(event) => onChange(event.target.value)} type="month" value={month} />
  </label>;
}

function BudgetUtilization({ budget }) {
  if (!budget) return null;
  return <section className="mf-card expenses-budget" aria-label="Uso del presupuesto">
    <div className="expenses-donut" style={{ "--expenses-percent": `${budget.percent ?? 0}%` }}><span>{budget.percent ?? "-"} %</span></div>
    <div className="expenses-budget-copy">
      <h2>Uso del presupuesto</h2>
      <p><strong>{formatMoney(budget.confirmed_expense_total)}</strong> confirmados de {formatMoney(budget.budget_total)}</p>
      <div className="mf-progress" aria-label={`${budget.percent ?? "Sin porcentaje"} del presupuesto utilizado`}><span className="mf-progress__value" style={{ "--mf-progress": `${budget.percent ?? 0}%` }} /></div>
      <p className="expenses-budget-caption">Porcentaje informado por el presupuesto mensual</p>
    </div>
  </section>;
}

function EmptyDashboard() {
  return <section className="mf-card mf-card--flat expenses-empty" role="status"><h2>Sin planificación para este mes</h2><p>No hay gastos previstos, movimientos confirmados ni pagos pendientes visibles para el mes seleccionado.</p></section>;
}

export function ExpensesDashboard({ dashboard, month, onAddExpense, onMonthChange, onViewMovements, status, onRetry }) {
  if (status === "loading" || status === "idle") return <section className="mf-card mf-card--flat expenses-status" aria-live="polite" role="status">Cargando gastos autorizados...</section>;
  if (status === "error") return <section className="mf-card mf-card--flat expenses-status" role="alert"><h2>No se pudieron cargar los gastos</h2><p>Verificá la conexión e intentá nuevamente.</p><button className="mf-button mf-button--secondary" onClick={onRetry} type="button">Reintentar</button></section>;

  const member = isMemberDashboard(dashboard);
  const hasContent = dashboard.categories.length || dashboard.upcoming_obligations.length || dashboard.forecast.total !== dashboard.confirmed.total;

  return <section className="expenses-page">
    <header className="expenses-header">
      <div className="expenses-brand"><span className="app-brand-mark"><WalletCards aria-hidden="true" /></span><p className="app-brand">Mosquera <strong>Finance</strong></p></div>
      <div className="expenses-title-row"><div><h1>Gastos de {formatMonth(month)}</h1><p>Control, categorías y próximos pagos</p></div><MonthPicker month={month} onChange={onMonthChange} /></div>
    </header>

    <section className="mf-card mf-card--accent expenses-hero">
      <div><p className="mf-eyebrow">Previsto, no confirmado</p><h2>Gastos mensuales previstos</h2><p className="mf-amount mf-amount--accent">{formatMoney(dashboard.forecast.total)}</p></div>
      <div className="expenses-responsibility">
        {dashboard.responsibility.items.map((item) => <div key={item.member}><UserRound aria-hidden="true" /><span>{item.member}</span><strong>{formatMoney(item.amount)}</strong></div>)}
        {dashboard.responsibility.setup_required && <p>Faltan asignaciones completas en algunos gastos compartidos.</p>}
        {member && !dashboard.responsibility.items.length && <p>Solo se muestran tus responsabilidades autorizadas.</p>}
      </div>
      <p className="expenses-confirmed">Confirmado este mes: <strong>{formatMoney(dashboard.confirmed.total)}</strong></p>
    </section>

    <BudgetUtilization budget={dashboard.budget_utilization} />
    {!hasContent && <EmptyDashboard />}

    {dashboard.categories.length > 0 && <section className="mf-card expenses-categories"><h2><Coins aria-hidden="true" /> Gastos por categoría</h2><div>{dashboard.categories.map((category, index) => <article key={`${category.source}-${category.name}-${index}`}><span className="expenses-category-icon"><CategoryIcon name={category.name} /></span><div><h3>{category.name}</h3><p>{category.source === "BUDGET" ? "Presupuesto mensual" : "Previsto, no confirmado"}</p></div><strong>{formatMoney(category.amount)}</strong><ChevronRight aria-hidden="true" /></article>)}</div></section>}

    {dashboard.upcoming_obligations.length > 0 && <section className="mf-card expenses-obligations"><h2><CalendarDays aria-hidden="true" /> Próximos pagos</h2><p>Pagos previstos ya materializados</p><div>{dashboard.upcoming_obligations.map((obligation) => <article key={`${obligation.due_on}-${obligation.category}`}><span>{obligation.category}</span><span>{formatDate(obligation.due_on)}</span><strong>{formatMoney(obligation.amount)}</strong><ChevronRight aria-hidden="true" /></article>)}</div></section>}

    <div className="expenses-actions"><button className="mf-button mf-button--secondary" onClick={onViewMovements} type="button"><List aria-hidden="true" />Ver movimientos</button><button className="mf-button" onClick={onAddExpense} type="button"><CirclePlus aria-hidden="true" />Añadir gasto</button></div>
  </section>;
}
