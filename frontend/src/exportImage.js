import { formatMoney } from "./formatMoney";

const WIDTH = 1080;
const HEIGHT = 1350;

function drawText(context, text, x, y, options = {}) {
  const { color = "#e2e8f0", font = "400 32px system-ui", maxWidth = WIDTH - 144, align = "left" } = options;
  context.fillStyle = color;
  context.font = font;
  context.textAlign = align;
  context.fillText(text, x, y, maxWidth);
}

function drawSection(context, title, records, y) {
  drawText(context, title.toUpperCase(), 72, y, { color: "#6ee7b7", font: "700 22px system-ui" });
  y += 46;

  if (!records.length) {
    drawText(context, "Sin movimientos registrados", 72, y, { color: "#94a3b8", font: "400 26px system-ui" });
    return y + 56;
  }

  for (const record of records.slice(0, 3)) {
    drawText(context, record.description || record.name || "Sin descripción", 72, y, { font: "600 29px system-ui", maxWidth: 700 });
    if (record.amount !== undefined) {
      drawText(context, formatMoney(record.amount) || "", 1008, y, { color: "#ffffff", font: "700 29px system-ui", maxWidth: 300, align: "right" });
    }
    y += 48;
  }

  if (records.length > 3) {
    drawText(context, `+ ${records.length - 3} más`, 72, y, { color: "#94a3b8", font: "400 24px system-ui" });
    y += 42;
  }
  return y + 28;
}

function canvasToBlob(canvas) {
  return new Promise((resolve, reject) => {
    canvas.toBlob((blob) => (blob ? resolve(blob) : reject(new Error("No se pudo crear la imagen."))), "image/png");
  });
}

export async function createExportImage(payload, familyName) {
  const canvas = document.createElement("canvas");
  canvas.width = WIDTH;
  canvas.height = HEIGHT;
  const context = canvas.getContext("2d");
  if (!context) {
    throw new Error("Tu navegador no permite crear la imagen.");
  }

  context.fillStyle = "#07111f";
  context.fillRect(0, 0, WIDTH, HEIGHT);
  context.fillStyle = "#102b29";
  context.beginPath();
  context.arc(WIDTH, 0, 360, 0, Math.PI * 2);
  context.fill();

  drawText(context, "MOSQUERA FINANCE", 72, 102, { color: "#6ee7b7", font: "700 25px system-ui" });
  drawText(context, `Resumen para ${payload.recipient}`, 72, 172, { color: "#ffffff", font: "700 52px system-ui" });
  drawText(context, familyName, 72, 218, { color: "#94a3b8", font: "400 28px system-ui" });
  drawText(context, new Intl.DateTimeFormat("es-ES", { dateStyle: "long" }).format(new Date()), 72, 262, { color: "#94a3b8", font: "400 24px system-ui" });

  let y = 346;
  y = drawSection(context, "Ingresos confirmados", payload.incomeMovements, y);
  y = drawSection(context, "Gastos confirmados", payload.expenseMovements, y);
  y = drawSection(context, "Objetivos de ahorro", payload.savingsGoals, y);

  if (payload.matiasFund && y < 1180) {
    drawText(context, "FONDO MATÍAS", 72, y, { color: "#6ee7b7", font: "700 22px system-ui" });
    drawText(context, "Saldo real", 72, y + 48, { font: "600 29px system-ui" });
    drawText(context, formatMoney(payload.matiasFund.real_balance) || "", 1008, y + 48, { color: "#ffffff", font: "700 29px system-ui", maxWidth: 300, align: "right" });
  }

  drawText(context, "Información autorizada al momento de generar esta tarjeta.", 72, 1270, { color: "#64748b", font: "400 21px system-ui" });
  return canvasToBlob(canvas);
}

export function downloadImage(file) {
  const url = URL.createObjectURL(file);
  const link = document.createElement("a");
  link.href = url;
  link.download = file.name;
  link.style.display = "none";
  document.body.append(link);
  link.click();
  setTimeout(() => {
    link.remove();
    URL.revokeObjectURL(url);
  }, 0);
}
