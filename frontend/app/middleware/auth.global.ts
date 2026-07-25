export default defineNuxtRouteMiddleware((to) => {
  // Client-facing share links (e.g. /p/[token]) are unauthenticated by
  // design — the token itself is the access boundary, not a session.
  if (to.meta.public) return;

  const authStore = useAuthStore();

  if (!authStore.user) {
    authStore.restoreSession();
  }

  if (!authStore.isAuthenticated && to.path !== "/") {
    return navigateTo("/");
  }
  if (authStore.isAuthenticated && to.path === "/") {
    return navigateTo("/dashboard");
  }
});
