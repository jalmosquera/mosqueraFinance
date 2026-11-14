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
