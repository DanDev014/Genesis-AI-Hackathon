import { apiRequest } from "~~/server/utils/request";

export default defineEventHandler(async (event) => {
  const body = await readBody(event);
  return apiRequest("/clients", { method: "POST", body });
});
