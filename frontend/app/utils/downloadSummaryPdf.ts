import {
  PDFDocument,
  StandardFonts,
  rgb,
} from "pdf-lib";

export async function downloadSummaryPdf(summary: any) {
  const meeting = summary.first_meeting_deliverables;
  const kp = meeting?.key_points ?? {};

  const pdf = await PDFDocument.create();

  let page = pdf.addPage([595.28, 841.89]); // A4

  const { width, height } = page.getSize();

  const font = await pdf.embedFont(StandardFonts.Helvetica);
  const bold = await pdf.embedFont(StandardFonts.HelveticaBold);

  const margin = 50;
  const lineHeight = 18;

  let y = height - margin;

  const ensureSpace = (required = 40) => {
    if (y < required) {
      page = pdf.addPage([595.28, 841.89]);
      y = height - margin;
    }
  };

  const title = (text: string) => {
    ensureSpace(60);

    page.drawText(text, {
      x: margin,
      y,
      size: 18,
      font: bold,
      color: rgb(0.18, 0.18, 0.18),
    });

    y -= 28;
  };

  const heading = (text: string) => {
    ensureSpace(40);

    page.drawText(text, {
      x: margin,
      y,
      size: 13,
      font: bold,
      color: rgb(0.72, 0.55, 0.05),
    });

    y -= 20;
  };

  const body = (text: string) => {
    ensureSpace();

    page.drawText(text, {
      x: margin,
      y,
      size: 11,
      font,
    });

    y -= lineHeight;
  };

  const bullet = (text: string) => {
    body(`• ${text}`);
  };

  // ------------------------------------
  // Header
  // ------------------------------------

  title("TAFSIRI");
  body("Meeting Summary");
  body(new Date(summary.created_at).toLocaleString());

  y -= 12;

  // ------------------------------------
  // Meeting
  // ------------------------------------

  heading("Meeting");
  body(`Title: ${meeting?.title || "—"}`);
  body(`Type: ${meeting?.meeting_type || "—"}`);
  y -= 8;

  // ------------------------------------
  // Client (only if extracted)
  // ------------------------------------

  if (kp.client) {
    heading("Client");
    body(`Company: ${kp.client.company || "—"}`);
    body(`Contact: ${kp.client.primary_contact || "—"}`);
    y -= 8;
  }

  // ------------------------------------
  // Project (only if extracted)
  // ------------------------------------

  if (kp.project) {
    heading("Project");
    body(`Name: ${kp.project.name || "—"}`);
    body(`Type: ${kp.project.type || "—"}`);
    body(`Objective: ${kp.project.objective || "—"}`);
    y -= 8;
  }

  // ------------------------------------
  // Deliverables (only if extracted)
  // ------------------------------------

  if (kp.deliverables?.length) {
    heading("Deliverables");
    kp.deliverables.forEach((item: any) => {
      bullet(`${item.name}${item.duration ? ` (${item.duration})` : ""}`);
    });
    y -= 8;
  }

  // ------------------------------------
  // Timeline (only if extracted)
  // ------------------------------------

  if (kp.timeline) {
    heading("Timeline");
    if (kp.timeline.hackathon_end) body(`Hackathon Ends: ${kp.timeline.hackathon_end}`);
    if (kp.timeline.summary_video_genesis_quote)
      body(`Summary Video: ${kp.timeline.summary_video_genesis_quote}`);
    if (kp.timeline.social_clips_genesis_quote)
      body(`Social Clips: ${kp.timeline.social_clips_genesis_quote}`);
    y -= 8;
  }

  // ------------------------------------
  // Creative Direction (only if extracted)
  // ------------------------------------

  if (kp.creative_direction) {
    heading("Creative Direction");
    if (kp.creative_direction.description) body(kp.creative_direction.description);
    (kp.creative_direction.messaging_themes ?? []).forEach((theme: string) => bullet(theme));
    y -= 8;
  }

  // ------------------------------------
  // Next Steps (only if extracted)
  // ------------------------------------

  if (kp.next_steps?.genesis?.length) {
    heading("Genesis Next Steps");
    kp.next_steps.genesis.forEach((step: string) => bullet(step));
    y -= 8;
  }

  if (kp.next_steps?.client?.length) {
    heading("Client Next Steps");
    kp.next_steps.client.forEach((step: string) => bullet(step));
    y -= 12;
  }

  // ------------------------------------
  // Budget (only if extracted)
  // ------------------------------------

  if (kp.budget) {
    heading("Budget");
    body(kp.budget.status || "Not yet established.");
    y -= 8;
  }

  // ------------------------------------
  // Competition (only if extracted)
  // ------------------------------------

  if (kp.competition) {
    heading("Competition");
    if (kp.competition.other_agencies)
      body(`Other Agencies: ${kp.competition.other_agencies}`);
    if (kp.competition.selection_method)
      body(`Selection: ${kp.competition.selection_method}`);
  }

  // ------------------------------------
  // Fallback — a plain transcript that only yielded participants/action
  // items, not a full structured extraction.
  // ------------------------------------

  if (!kp.client && !kp.project && !kp.deliverables?.length && !kp.timeline && !kp.budget) {
    if (kp.participants?.length) {
      heading("Participants");
      body(kp.participants.join(", "));
      y -= 8;
    }
    if (kp.action_items?.length) {
      heading("Action Items");
      kp.action_items.forEach((item: string) => bullet(item));
    }
  }

  // ------------------------------------
  // Footer
  // ------------------------------------

  page.drawLine({
    start: { x: margin, y: 40 },
    end: { x: width - margin, y: 40 },
    thickness: 1,
  });

  page.drawText("Generated by Tafsiri", {
    x: margin,
    y: 22,
    size: 10,
    font,
    color: rgb(0.45, 0.45, 0.45),
  });

  const bytes = await pdf.save();

  const blob = new Blob([bytes as BlobPart], {
    type: "application/pdf",
  });

  const url = URL.createObjectURL(blob);

  const link = document.createElement("a");

  link.href = url;

  link.download = `${(meeting?.title || "summary").replace(/\s+/g, "_")}_summary.pdf`;

  link.click();

  URL.revokeObjectURL(url);
}
