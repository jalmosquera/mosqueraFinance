const eurFormatter = new Intl.NumberFormat("es-ES", {
  style: "currency",
  currency: "EUR",
  minimumFractionDigits: 2,
  maximumFractionDigits: 2
});

export function formatMoney(amount) {
  if (typeof amount !== "string" && typeof amount !== "number") {
    return null;
  }

  const value = String(amount);
  if (!/^-?\d+(\.\d{1,2})?$/.test(value)) {
    return null;
  }

  return eurFormatter.format(Number(value));
}
