import type { Collections } from '@nuxt/content'

export const useNavigation = async () => {
  const route = useRoute()

  const collection = computed(() => {
    return route.path.split('/')
      .find(segment => segment.length > 0) as Exclude<keyof Collections, 'index'>
  })

  const { data: navigation } = await useAsyncData(`navigation-${collection.value}`, () => {
    return queryCollectionNavigation(collection.value)
  }, {
    transform: (data) => {
      return data?.find(item => item.path === `/${collection.value}`)?.children || data || []
    },
    watch: [collection],
  })

  return {
    collection,
    navigation,
  }
}
