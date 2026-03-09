/**
 * Composable for managing cache groups.
 */
import type { TableColumn } from '@nuxt/ui'

const useCacheGroups = () => {
  const route = useRoute()
  const router = useRouter()

  const { t: $t } = useI18n()

  /** Reactive query object */
  const query = computed<CacheGroupsSearchQuery>(() => normalizeCacheGroupsQuery(route.query))
  /** Update query parameters and push to router */
  const updateQuery = (newQuery: Partial<CacheGroupsSearchQuery>) => {
    router.push({
      query: {
        ...route.query,
        ...newQuery,
      },
    })
  }

  const searchTerm = ref(query.value.q)
  const filter = ref(query.value.f)
  const pageSize = ref(query.value.l)

  const searchIdentityKey = computed(() => {
    const { p, l, ...filters } = query.value
    return JSON.stringify(filters)
  })

  const selectedMap = useState<Record<string, boolean>>(
    `selection:${searchIdentityKey.value}`, () => ({}),
  )

  /** Column names with translations */
  const columnNames = {
    id: '#',
    displayName: $t('cache-groups.table.column.repository-name'),
    serviceURL: $t('cache-groups.table.column.repository-url'),
    updated: $t('cache-groups.table.column.repository-updated-at'),
  }

  type CacheGroupsTableColumn = TableColumn<CacheGroupsSummary>
  const columns = computed<CacheGroupsTableColumn[]>(() => [
    {
      accessorKey: 'name',
      header: columnNames.displayName,
    },
    {
      accessorKey: 'url',
      header: columnNames.serviceURL,
    },
    {
      accessorKey: 'updated',
      header: columnNames.updated,
    },
  ])

  return {
    query,
    updateQuery,
    criteria: {
      searchTerm,
      filter,
      pageSize,
    },
    selectedMap,
    columns,
  }
}

export { useCacheGroups }
