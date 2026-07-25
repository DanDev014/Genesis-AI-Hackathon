export default defineNuxtConfig({
  modules: ['@nuxt/eslint', '@nuxt/ui', '@pinia/nuxt'],

  devtools: {
    enabled: true
  },

  app: {
    head: {
      title: 'Kora AI',
      link: [
        { rel: 'icon', type: 'image/svg+xml', href: '/favicon.svg' }
      ]
    }
  },

  css: ['~/assets/css/main.css'],

  vite: {
    resolve: {
      // html2pdf.js hardcodes `require("html2canvas")`, which doesn't support
      // modern CSS color functions (oklch/oklab/lab/lch) that Chrome now uses
      // for some of its own default/system colors. html2canvas-pro is a
      // drop-in fork that adds support for them.
      alias: {
        html2canvas: 'html2canvas-pro'
      }
    }
  },

  routeRules: {
    '/': { prerender: true }
  },
  runtimeConfig: {
    apiBaseUrl: process.env.API_BASE_URL,
    agentBaseUrl: process.env.AGENT_BASE_URL
  },
  compatibilityDate: '2026-06-30',

  eslint: {
    config: {
      stylistic: {
        commaDangle: 'never',
        braceStyle: '1tbs'
      }
    }
  }
})