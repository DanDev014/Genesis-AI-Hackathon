import { apiRequest } from "~~/server/utils/request";

export default defineEventHandler(async (event) => {
  const id = getRouterParam(event, "id");
  const body = await readBody<{
    outcome: "pending" | "won" | "lost";
    notes?: string;
    user_id?: number;
  }>(event);

  return apiRequest(`/proposals/${id}/outcome`, {
    method: "POST",
    body,
  });
});
