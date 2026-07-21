export default defineEventHandler(async (event) => {
  const body = await readBody<{
    transcript: string;
    meetingType: string;
    clientId: number;
  }>(event);

  try {
    console.log("Incoming request:", body);

    /**
     * Step 1:
     * Convert the raw transcript into structured JSON.
     */
    const scriptResponse = await agentRequest<{
      ok: boolean;
      captured: Record<string, unknown>;
    }>("/webhook/fathom/script", {
      method: "POST",
      body: body.transcript,
      headers: {
        "Content-Type": "text/plain",
        Accept: "application/json",
      },
    });

    console.log("Script response:", scriptResponse);

    /**
     * Step 2:
     * Send the structured JSON to the AI workflow.
     * This generates the final meeting summary that will be stored.
     */
    const summaryResponse = await agentRequest("/webhook/fathom", {
      method: "POST",
      body: scriptResponse,
      headers: {
        Accept: "application/json",
      },
    });

    console.log("Summary response:", summaryResponse);

    /**
     * ==========================================================
     * TODO:
     * Once the Flask endpoint is available, persist the summary.
     * ==========================================================
     */

    // const savedSummary = await apiRequest("/summaries", {
    //   method: "POST",
    //   body: {
    //     client_id: body.clientId,
    //     first_meeting_deliverables: summaryResponse.captured,
    //   },
    // });

    // return savedSummary;

    /**
     * Temporary response while the persistence endpoint
     * is still under development.
     */
    return {
      success: true,
      clientId: body.clientId,
      summary: summaryResponse,
    };
  } catch (error) {
    console.error("Generate summary error:", error);

    throw createError({
      statusCode: 500,
      statusMessage: "Failed to generate meeting summary.",
    });
  }
});