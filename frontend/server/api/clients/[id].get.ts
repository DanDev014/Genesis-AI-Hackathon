import { apiRequest } from "~~/server/utils/request";
export default defineEventHandler(async (event) => {
  const id = getRouterParam(event, "id");
  return apiRequest(`/clients/${id}`);
});
