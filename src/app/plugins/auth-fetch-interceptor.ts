/*
 * Copyright (C) 2026 National Institute of Informatics.
 */

/**
 * Nuxt plugin to intercept fetch requests for authentication handling
 */
export default defineNuxtPlugin(() => {
  const { baseURL } = useAppConfig()
  const { handleFetchError } = useErrorHandling()

  globalThis.$fetch = $fetch.create({
    baseURL,
    credentials: 'include',
    onResponseError: ({ response }) => handleFetchError({ response }),
  })
})
