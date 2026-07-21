import { apiRequest } from "~~/server/utils/request";

export default defineEventHandler(async (event) => {
  const query = getQuery(event);
  return apiRequest('/clients', { query });
});