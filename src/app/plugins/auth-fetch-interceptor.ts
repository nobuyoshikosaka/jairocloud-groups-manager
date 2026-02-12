/*
 * Copyright (C) 2026 National Institute of Informatics.
 */

/**
 * Nuxt plugin to intercept fetch requests for authentication handling
 */
export default defineNuxtPlugin(() => {
  const { baseURL } = useAppConfig()

  const { checkout } = useAuth()

  const publicRoutes = new Set(['/login'])

  globalThis.$fetch = $fetch.create({
    baseURL,
    credentials: 'include',

    onResponseError: async ({ response }) => {
      const route = useRoute()
      const statusCode = response.status
      if (statusCode === 401 && !publicRoutes.has(route.path.replace(/\/$/, ''))) {
        const next = encodeURIComponent(route.fullPath.replace(/\/$/, ''))
        await checkout({ next })
      }
    },
  })
})
