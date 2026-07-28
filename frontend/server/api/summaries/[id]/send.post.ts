import { apiRequest } from "~~/server/utils/request";

export default defineEventHandler(async (event) => {
  const id = getRouterParam(event, "id");
  const body = await readBody<{
    to_emails: string[];
    subject?: string;
    message?: string;
  }>(event);

  return apiRequest(`/summaries/${id}/send`, {
    method: "POST",
    body,
  });
});
