import { apiRequest } from "~~/server/utils/request";

export default defineEventHandler(async (event) => {
  const id = getRouterParam(event, "id");
  const body = await readBody<{
    to_email: string;
    subject?: string;
    message?: string;
  }>(event);

  return apiRequest(`/proposals/${id}/send`, {
    method: "POST",
    body,
  });
});
