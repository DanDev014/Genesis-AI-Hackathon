import { agentRequest } from "~~/server/utils/agentRequest";

/**
 * Stateless counterpart to render-proposal.post.ts — see that file.
 */
export default defineEventHandler(async (event) => {
  const body = await readBody(event);

  return await agentRequest<string>("/render/quote-preview.html", {
    method: "POST",
    body,
  });
});
