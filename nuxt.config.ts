// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  modules: [
    '@nuxt/eslint',
    '@nuxt/test-utils',
    '@nuxt/ui',
  ],
  ssr: false,
  devtools: { enabled: false },
  app: {
    baseURL: '/',
  },
  css: ['~/assets/css/main.css'],
  build: {
    transpile: ['@@nuxt/ui'],
  },
  compatibilityDate: '2025-07-15',
  nitro: {
    preset: 'static',
  },
  eslint: {
    config: {
      stylistic: true,
    },
  },
})
