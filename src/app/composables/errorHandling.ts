import type { FetchResponse } from 'ofetch'

const useErrorHandling = () => {
  const route = useRoute()
  const toast = useToast()
  const { t: $t } = useI18n()

  const { publicRoutes } = useAppConfig()
  const { checkout } = useAuth()

  const handleFetchError = async ({ response }: { response: FetchResponse<unknown> }) => {
    switch (response.status) {
      case 400: {
        toast.add({
          title: $t('toast.error.bad-request.title'),
          description: $t('toast.error.bad-request.description'),
          color: 'error',
          icon: 'i-lucide-circle-x',
        })
        break
      }
      case 401: {
        toast.add({
          title: $t('toast.error.unauthorized.title'),
          description: $t('toast.error.unauthorized.description'),
          color: 'error',
          icon: 'i-lucide-circle-x',
        })
        if (!publicRoutes.has(route.path.replace(/\/$/, ''))) {
          const next = encodeURIComponent(route.fullPath.replace(/\/$/, ''))
          await checkout({ next })
        }
        break
      }
      case 403: {
        toast.add({
          title: $t('toast.error.forbidden.title'),
          description: $t('toast.error.forbidden.description'),
          color: 'error',
          icon: 'i-lucide-circle-x',
        })
        break
      }
      case 404: {
        toast.add({
          title: $t('toast.error.not-found.title'),
          description: $t('toast.error.not-found.description'),
          color: 'error',
          icon: 'i-lucide-circle-x',
        })
        break
      }
      case 503: {
        toast.add({
          title: $t('toast.error.service-unavailable.title'),
          description: $t('toast.error.service-unavailable.description'),
          color: 'error',
          icon: 'i-lucide-circle-x',
        })
        break
      }
      default: {
        toast.add({
          title: $t('toast.error.server.title'),
          description: $t('toast.error.server.description'),
          color: 'error',
          icon: 'i-lucide-circle-x',
        })
        break
      }
    }
  }

  return { handleFetchError }
}

export { useErrorHandling }
