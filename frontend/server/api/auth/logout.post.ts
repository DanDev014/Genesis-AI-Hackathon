export default defineEventHandler(async (event) => {
  deleteCookie(event, "session_user", { path: "/" });
  return sendRedirect(event, "/", 302);
});
