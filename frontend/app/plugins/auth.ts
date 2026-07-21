export default defineNuxtPlugin(() => {
  const authStore = useAuthStore();
  authStore.restoreSession();
});