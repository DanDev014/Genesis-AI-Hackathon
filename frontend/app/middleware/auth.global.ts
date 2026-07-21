export default defineNuxtRouteMiddleware((to) => {
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
