const categoryIcons = [
  [/alquiler|vivienda|casa/i, "House"],
  [/aliment|supermercado|comida/i, "ShoppingCart"],
  [/luz|electric|energ/i, "Zap"],
  [/internet|spotify|chatgpt|suscrip/i, "CreditCard"],
  [/peluquer|cuidado/i, "Scissors"]
];

export function categoryIconName(categoryName) {
  return categoryIcons.find(([pattern]) => pattern.test(categoryName))?.[1] || "Ellipsis";
}

export function isMemberDashboard(dashboard) {
  return dashboard?.visibility?.role === "MEMBER";
}
