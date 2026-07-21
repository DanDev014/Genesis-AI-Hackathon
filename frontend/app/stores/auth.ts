import { defineStore } from 'pinia';

interface AuthUser {
  user_id: number;
  email: string;
  user_type: string;
}

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: null as AuthUser | null,
    loading: false,
  }),

  getters: {
    isAuthenticated: (state) => !!state.user,
  },

  actions: {
    async login(email: string, password: string) {
      this.loading = true;
      try {
        const response = await $fetch<{ user: AuthUser }>('/api/auth/login', {
          method: 'POST',
          body: { email, password },
        });
        this.user = response.user;
        return response;
      } finally {
        this.loading = false;
      }
    },

    async logout() {
      await $fetch('/api/auth/logout', { method: 'POST' });
      this.user = null;
      await navigateTo('/');
    },

    restoreSession() {
      const cookie = useCookie<string | null>('session_user');
      if (cookie.value) {
        try {
          this.user = typeof cookie.value === 'string'
            ? JSON.parse(cookie.value)
            : cookie.value;
        } catch {
          this.user = null;
        }
      }
    },
  },
});