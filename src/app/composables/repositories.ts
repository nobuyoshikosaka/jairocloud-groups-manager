/**
 * Composable for repository-related operations
 */

import { UButton, UDropdownMenu, UIcon, ULink } from '#components'

import type { ButtonProps, DropdownMenuItem, TableColumn, TableRow } from '@nuxt/ui'

const useRepositoriesTable = () => {
  const route = useRoute()

  const toast = useToast()
  const { t: $t } = useI18n()
  const { copy } = useClipboard()

  /** Reactive query object */
  const query = computed<RepositoriesSearchQuery>(() => normalizeRepositoriesQuery(route.query))
  /** Update query parameters and push to router */
  const updateQuery = async (newQuery: Partial<RepositoriesSearchQuery>) => {
    await navigateTo({
      query: {
        ...route.query,
        ...newQuery,
      },
    })
  }

  const searchTerm = ref(query.value.q)
  const spConnectorId = ref(query.value.i)
  const sortKey = computed(() => query.value.k)
  const sortOrder = computed(() => query.value.d)
  const pageNumber = ref(query.value.p)
  const pageSize = ref(query.value.l)

  /** Column names with translations */
  const columnNames: Record<keyof RepositorySummary, string> = {
    id: '#',
    serviceName: $t('repositories.table.column.service-name'),
    serviceUrl: $t('repositories.table.column.service-url'),
    spConnectorId: $t('repositories.table.column.sp-connector-id'),
    entityIds: $t('repositories.table.column.entity-ids'),
  }

  /** Returns action buttons for a repository entry */
  const creationButtons = computed<ButtonProps[]>(() => [
    {
      icon: 'i-lucide-plus',
      label: $t('button.create-new'),
      to: '/repositories/new',
      color: 'primary',
      variant: 'solid',
    },
  ])

  /** Actions to display when the list is empty */
  const emptyActions = computed<ButtonProps[]>(() => [
    {
      icon: 'i-lucide-refresh-cw',
      label: $t('button.reload'),
      color: 'neutral',
      variant: 'subtle',
      onClick: () => {}, // Placeholder for reload action
    },
  ])

  type RepositoryTableColumn = TableColumn<RepositorySummary>
  const columns = computed<RepositoryTableColumn[]>(() => [
    {
      accessorKey: 'id',
      header: () => sortableHeader('id'),
      cell: ({ row }) => row.original.spConnectorId,
    },
    {
      accessorKey: 'serviceName',
      header: () => sortableHeader('serviceName'),
      cell: ({ row }) => {
        const name: string = row.original.serviceName
        return h(ULink, {
          to: `/repositories/${row.original.id}`,
          class: 'font-bold hover:underline inline-flex items-center',
        }, [
          h('span', name),
        ])
      },
      enableHiding: false,
    },
    {
      accessorKey: 'serviceUrl',
      header: () => sortableHeader('serviceUrl'),
      cell: ({ row }) => {
        const url: string = row.original.serviceUrl
        return url
          ? h(ULink, {
              to: url,
              target: '_blank',
              class: 'hover:underline inline-flex items-center gap-1',
            }, [
              h('span', url),
              h(UIcon, { name: 'i-lucide-external-link', class: 'size-3 shrink-0' }),
            ])
          : undefined
      },
    },
    {
      accessorKey: 'entityIds',
      header: () => sortableHeader('entityIds'),
      cell: ({ row }) => row.original.entityIds?.[0],
    },
    {
      id: 'actions',
      header: '',
      cell: ({ row }) =>
        h(
          'div',
          { class: 'text-right' },
          h(
            // @ts-expect-error: props type mismatch
            UDropdownMenu,
            {
              'content': { align: 'end' },
              'items': getActionItems(row),
              'aria-label': 'Actions dropdown',
            },
            () =>
              h(UButton, {
                'icon': 'i-lucide-ellipsis-vertical',
                'color': 'neutral',
                'variant': 'ghost',
                'size': 'sm',
                'class': 'ml-auto',
                'aria-label': 'Actions dropdown',
              }),
          ),
        ),
      enableHiding: false,
    },
  ])

  function sortableHeader(key: RepositoriesSortableKeys) {
    const label = columnNames[key]
    const sortDirection = sortKey?.value === key ? sortOrder?.value : undefined
    const iconSet = {
      asc: 'i-lucide-arrow-down-a-z',
      desc: 'i-lucide-arrow-up-a-z',
      none: 'i-lucide-arrow-up-down',
    } as const

    return h(UButton, {
      color: sortDirection ? 'primary' : 'neutral',
      variant: 'ghost',
      size: 'xs',
      label,
      icon: sortDirection ? iconSet[sortDirection] : iconSet.none,
      class: 'font-medium cursor-pointer',
      onClick() {
        if (sortDirection === 'asc') updateQuery({ k: key, d: 'desc' }) // to desc
        else if (sortDirection === 'desc') updateQuery({ k: undefined, d: undefined }) // to default
        else updateQuery({ k: key, d: 'asc' }) // to asc
      },
    })
  }

  function getActionItems(row: TableRow<RepositorySummary>): DropdownMenuItem[] {
    return [
      {
        type: 'label',
        label: $t('table.actions-label'),
      },
      {
        label: $t('repository.actions.copy-url'),
        onSelect() {
          copy(row.original.serviceUrl)

          toast.add({
            title: $t('repository.actions.copy-url-success'),
            color: 'success',
            icon: 'i-lucide-circle-check',
          })
        },
        icon: 'i-lucide-clipboard-copy',
      },
      {
        label: $t('repositories.actions.copy-sp-connector-id'),
        onSelect() {
          copy(row.original.spConnectorId!)

          toast.add({
            title: $t('repositories.actions.copy-sp-connector-id-success'),
            color: 'success',
            icon: 'i-lucide-circle-check',
          })
        },
        icon: 'i-lucide-clipboard-copy',
      },
      {
        type: 'separator',
      },
      {
        label: $t('table.actions.view-details'),
        to: `/repositories/${row.original.id}`,
        icon: 'i-lucide-eye',
      },
    ]
  }

  const columnVisibility = ref({ id: false })

  const makePageInfo = (result: Ref<RepositoriesSearchResult | undefined>) => {
    return computed(() => {
      const start = result.value?.offset ?? 1
      const total = result.value?.total ?? 0
      const end = Math.min(start + pageSize.value!, total)

      return `${start} - ${end} / ${total}`
    })
  }

  return {
    query,
    updateQuery,
    criteria: {
      searchTerm,
      spConnectorId,
      sortKey,
      sortOrder,
      pageNumber,
      pageSize,
    },
    creationButtons,
    emptyActions,
    columns,
    columnNames,
    columnVisibility,
    makePageInfo,
  }
}

export { useRepositoriesTable }
