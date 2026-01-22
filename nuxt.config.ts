// https://nuxt.com/docs/api/configuration/nuxt-config
export default defineNuxtConfig({
  modules: [
    '@nuxt/eslint',
    '@nuxt/ui',
    '@nuxt/content',
    '@pinia/nuxt',
    '@nuxtjs/i18n',
    '@nuxt/test-utils',
  ],

  devtools: {
    enabled: true,
  },

  css: ['~/assets/css/main.css'],

  srcDir: 'src/app/',

  routeRules: {
    '/': { prerender: true },
  },

  compatibilityDate: '2026-01-10',

  vite: {
    server: {
      allowedHosts: [
        't2dxtvk5-3000.asse.devtunnels.ms', 'localhost',
      ],
      hmr: {
        host: 't2dxtvk5-3000.asse.devtunnels.ms',
        protocol: 'wss',
        port: 443,
      },
    },
  },

  eslint: {
    config: {
      stylistic: true,
    },
  },

  i18n: {
    locales: [
      { code: 'en', iso: 'es-US', file: 'en.json', name: 'English' },
      { code: 'ja', iso: 'ja-JP', file: 'ja.json', name: '日本語' },
    ],
    defaultLocale: 'ja',
    strategy: 'no_prefix',
    detectBrowserLanguage: {
      fallbackLocale: 'ja',
    },
    restructureDir: 'src/app/i18n',
  },
})
