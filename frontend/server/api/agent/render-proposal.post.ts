import { agentRequest } from "~~/server/utils/agentRequest";

/**
 * Fetches the branded proposal HTML from genesis_agent's stateless render
 * endpoint, so "Download PDF" always has the real branded template to
 * capture instead of falling back to a plain bullet-point PDF.
 */
export default defineEventHandler(async (event) => {
  const body = await readBody(event);

  return await agentRequest<string>("/render/proposal-preview.html", {
    method: "POST",
    body,
  });
});
