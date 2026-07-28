import html2pdf from "html2pdf.js";

const A4_WIDTH_PX = 794;
const A4_HEIGHT_PX = 1123;

/** Renders a full HTML document (genesis_agent's branded Jinja template)
 * into a downloaded PDF by loading it into an off-screen iframe and
 * capturing it with html2canvas/html2pdf. Returns false (never throws) if
 * the capture didn't produce anything to save, so callers can fall back
 * to a simpler PDF instead of leaving the user with nothing. */
export async function renderBrandedHtmlToPdf(html: string, filename: string): Promise<boolean> {
  const iframe = document.createElement("iframe");
  iframe.style.position = "fixed";
  iframe.style.left = "-10000px";
  iframe.style.top = "0";
  iframe.style.width = `${A4_WIDTH_PX}px`;
  iframe.style.height = `${A4_HEIGHT_PX}px`;
  iframe.style.border = "none";
  document.body.appendChild(iframe);

  try {
    await new Promise<void>((resolve) => {
      iframe.onload = () => resolve();
      iframe.srcdoc = html;
    });

    // `onload` only guarantees the iframe's DOM has parsed, not that layout/paint
    // has settled — give the browser two frames before handing it to html2canvas,
    // otherwise the capture can come back blank.
    await new Promise<void>((resolve) => {
      requestAnimationFrame(() => requestAnimationFrame(() => resolve()));
    });

    const target = iframe.contentDocument?.body;
    if (!target) return false;

    await html2pdf()
      .set({
        margin: 0,
        filename,
        html2canvas: { scale: 2, useCORS: true, windowWidth: A4_WIDTH_PX },
        jsPDF: { unit: "pt", format: "a4", orientation: "portrait" },
      })
      .from(target)
      .save();

    return true;
  } finally {
    document.body.removeChild(iframe);
  }
}
