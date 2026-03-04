/*
 * Copyright (C) 2026 National Institute of Informatics.
 */

export default defineNuxtRouteMiddleware(async (to, from) => {
  const { checkin } = useAuth()

  return await checkin({ to, from })
})
