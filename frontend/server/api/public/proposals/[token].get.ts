import { apiRequest } from "~~/server/utils/request";

export default defineEventHandler(async (event) => {
  const token = getRouterParam(event, "token");
  return apiRequest(`/public/proposals/${token}`);
});
