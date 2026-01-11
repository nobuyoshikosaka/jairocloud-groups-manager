/*
 * Copyright (C) 2026 National Institute of Informatics.
 */

import type { RouteLocationNormalizedGeneric } from 'vue-router'

/** Public routes that do not require authentication */
const publicRoutes = new Set(['/login'])
/** Path to redirect after successful login */
const loggedinRedirectPath = '/repositories'

/**
 * Composable for managing authentication state and actions
 */
export function useAuth() {
  const router = useRouter()

  const authStore = useAuthStore()
  const { isAuthenticated, authChecked, currentUser } = useAuthStore()

  const checkin = async ({
    to,
    from,
  }: {
    to: RouteLocationNormalizedGeneric
    from: RouteLocationNormalizedGeneric

  }) => {
    const next = encodeURIComponent(to.fullPath.replace(/\/$/, ''))
    const toPath = to.path.replace(/\/$/, '')
    const fromPath = from.path.replace(/\/$/, '')

    if (publicRoutes.has(to.path.replace(/\/$/, ''))) {
      return
    }

    if (!authChecked.value || fromPath === '/login') {
      try {
        const user = await $fetch<LoginUser>('/api/auth/check', { method: 'GET' })
        authStore.setUser(user)
        // return
      }
      catch {
        authStore.unsetUser()
      }
    }

    if (isAuthenticated.value) {
      let { next } = to.query
      if (Array.isArray(next)) {
        next = next[0]
      }

      if (next && !publicRoutes.has(next as string)) {
        router.push(next as string)
        return
      }

      if (!toPath) {
        router.push(loggedinRedirectPath)
        return
      }

      return
    }

    router.push({ path: '/login', query: next ? { next } : {} })
  }

  const checkout = () => {
    const route = useRoute()
    authStore.unsetUser()
    const next = encodeURIComponent(route.fullPath.replace(/\/$/, ''))
    router.push({ path: '/login', query: next ? { next } : {} })
  }

  const logout = async () => {
    try {
      await $fetch('/api/auth/logout', { method: 'POST' })
    }
    catch {
      // ignore errors
    }
    finally {
      checkout()
    }
  }

  return {
    /** Indicates whether the user is authenticated */
    isAuthenticated,
    /** Indicates whether the authentication check has been completed */
    authChecked,
    /** Current user information */
    currentUser,
    /** Checks the authentication status and navigates accordingly */
    checkin,
    /** Clears the authentication state */
    checkout,
    /** Logs out the user and redirects to the login page */
    logout,
  }
}
