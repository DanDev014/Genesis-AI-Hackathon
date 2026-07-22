export default defineEventHandler(async (event) => {
  const body = await readBody<{
    transcript: string;
    meetingType: string;
    clientId: number;
    userId: number;
  }>(event);

  try {
    console.log("Incoming request:", body);

    if (!body.transcript?.trim()) {
      throw createError({
        statusCode: 400,
        statusMessage: "Transcript is required.",
      });
    }

    /**
     * Step 1:
     * Convert the raw transcript into structured JSON.
     */
    const scriptResponse = await agentRequest<{
      ok: boolean;
      meeting_type?: string;
      captured?: Record<string, any>;
      reason?: string;
    }>(
      `/webhook/fathom/script?meeting_type=${encodeURIComponent(
        body.meetingType,
      )}`,
      {
        method: "POST",
        body: body.transcript,
        headers: {
          "Content-Type": "text/plain",
          Accept: "application/json",
        },
      },
    );

    console.log("Script response:", scriptResponse);

    if (!scriptResponse.ok || !scriptResponse.captured) {
      throw createError({
        statusCode: 400,
        statusMessage:
          scriptResponse.reason ?? "Unable to process the meeting transcript.",
        data: {
          error:
            scriptResponse.reason ??
            "Unable to process the meeting transcript.",
        },
      });
    }

    /**
     * Normalize meeting type.
     *
     * The script endpoint currently returns "discovery_call",
     * while the summary endpoint expects "discovery_meeting".
     */
    if (scriptResponse.meeting_type === "discovery_call") {
      scriptResponse.meeting_type = "discovery_meeting";
    }

    if (scriptResponse.captured.meeting_type === "discovery_call") {
      scriptResponse.captured.meeting_type = "discovery_meeting";
    }

    /**
     * Step 2:
     * Generate the discovery summary.
     */
    const summaryResponse = await agentRequest<{
      ok: boolean;
      captured?: Record<string, unknown>;
      reason?: string;
    }>("/webhook/fathom", {
      method: "POST",
      body: scriptResponse,
      headers: {
        Accept: "application/json",
      },
    });

    console.log("Summary response:", summaryResponse);

    if (!summaryResponse.ok || !summaryResponse.captured) {
      throw createError({
        statusCode: 400,
        statusMessage:
          summaryResponse.reason ?? "Failed to generate meeting summary.",
        data: {
          error:
            summaryResponse.reason ?? "Failed to generate meeting summary.",
        },
      });
    }

    /**
     * Step 3:
     * Persist the summary.
     */
    const savedSummary = await apiRequest("/summaries", {
      method: "POST",
      body: {
        user_id: body.userId,
        client_id: body.clientId,
        first_meeting_deliverables: scriptResponse.captured,
      },
    });

    return savedSummary;
  } catch (error: any) {
    console.error("=== SUMMARY GENERATION ERROR ===");
    console.error(error);

    if (error?.data) {
      console.error("Response body:", error.data);
    }

    if (error?.response?._data) {
      console.error("Response body:", error.response._data);
    }

    if (error?.statusCode) {
      throw error;
    }

    throw createError({
      statusCode: 500,
      statusMessage: "Failed to generate meeting summary.",
      data: {
        error: "Something went wrong while generating the meeting summary.",
      },
    });
  }
});
