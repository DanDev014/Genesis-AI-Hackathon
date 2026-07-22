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
      proposal?: Record<string, any>;
      quote?: Record<string, any>;
      proposal_html?: string;
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
     */
    if (scriptResponse.meeting_type === "discovery_call") {
      scriptResponse.meeting_type = "discovery_meeting";
    }

    if (scriptResponse.captured.meeting_type === "discovery_call") {
      scriptResponse.captured.meeting_type = "discovery_meeting";
    }

    /**
     * Route to the appropriate workflow.
     */
    if (body.meetingType === "internal") {
      return await handleInternalMeeting({
        body,
        scriptResponse,
      });
    }

    return await handleDiscoveryMeeting({
      body,
      scriptResponse,
    });
  } catch (error: any) {
    console.error("=== AI WORKFLOW ERROR ===");
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
      statusMessage: "Failed to process meeting.",
      data: {
        error: "Something went wrong while processing the meeting.",
      },
    });
  }
});

/**
 * ============================================================
 * Discovery Meeting Workflow
 * ============================================================
 */

async function handleDiscoveryMeeting({
  body,
  scriptResponse,
}: {
  body: {
    transcript: string;
    meetingType: string;
    clientId: number;
    userId: number;
  };
  scriptResponse: any;
}) {
  /**
   * Generate summary.
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
        error: summaryResponse.reason ?? "Failed to generate meeting summary.",
      },
    });
  }

  /**
   * Persist summary.
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
}

/**
 * ============================================================
 * Internal Meeting Workflow
 * ============================================================
 */

async function handleInternalMeeting({
  body,
  scriptResponse,
}: {
  body: {
    transcript: string;
    meetingType: string;
    clientId: number;
    userId: number;
  };
  scriptResponse: any;
}) {
  /**
   * Step 1:
   * Persist the proposal.
   *
   * Flask wraps every create response as {success, message, data}, not the
   * bare record — unwrap it here so the rest of this function (and the
   * frontend modal) always deals with a flat proposal object.
   */
  const proposalResponse = await apiRequest<{
    success: boolean;
    message: string;
    data: Record<string, any>;
  }>("/proposals", {
    method: "POST",
    body: {
      client_id: body.clientId,
      user_id: body.userId,

      scope_of_work: scriptResponse.proposal.scope,

      deliverables_list: scriptResponse.proposal.deliverables,

      timeline_milestones: scriptResponse.proposal.timeline,

      generated_by: "AI-drafted",

      status: scriptResponse.proposal.status,
    },
  });
  const savedProposal = proposalResponse.data;

  /**
   * Step 2:
   * Persist the quotation. Same unwrapping applies.
   */
  const quoteResponse = await apiRequest<{
    success: boolean;
    message: string;
    data: Record<string, any>;
  }>("/quotes", {
    method: "POST",
    body: {
      proposal_id: savedProposal.proposal_id,

      user_id: body.userId,

      currency: scriptResponse.quote.currency ?? "KES",

      tax_rate: 16,

      discount_amount: 0,

      total_amount: scriptResponse.quote.total,

      validity_days: 30,

      status: scriptResponse.quote.status,

      line_items: scriptResponse.quote.line_items,
    },
  });
  const savedQuote = quoteResponse.data;

  /**
   * Step 3:
   * Return the persisted entities together with the proposal HTML.
   */
  return {
    success: true,

    proposal: {
      ...savedProposal,
      proposal_html: scriptResponse.proposal_html,
    },

    quotation: savedQuote,
  };
}
