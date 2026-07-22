import { apiRequest } from "~~/server/utils/request";

export default defineEventHandler(async (event) => {
  const id = getRouterParam(event, "id");
  const body = await readBody(event);

  return apiRequest(`/quotes/${id}`, {
    method: "PATCH",
    body,
  });
});
