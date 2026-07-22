import { apiRequest } from "~~/server/utils/request";

export default defineEventHandler(async () => {
  return apiRequest("/dashboard");
});
