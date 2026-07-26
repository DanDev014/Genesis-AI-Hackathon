import { apiRequest } from "~~/server/utils/request";

export default defineEventHandler(async (event) => {
  const id = getRouterParam(event, "id");
  const body = await readBody<{ user_id?: number }>(event);

  return apiRequest(`/quotes/${id}/send-to-quickbooks`, {
    method: "POST",
    body,
  });
});
