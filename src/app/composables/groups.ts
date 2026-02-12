/**
 * Composable for group-related operations
 */

import { UButton, UCheckbox, UDropdownMenu, ULink } from '#components'

import type { Row } from '@tanstack/table-core'
import type { ButtonProps, DropdownMenuItem, TableColumn, TableRow } from '@nuxt/ui'

const useGroupsTable = () => {
  const route = useRoute()

  const toast = useToast()
  const { t: $t } = useI18n()
  const { copy } = useClipboard()

  /** Reactive query object */
  const query = computed<GroupsSearchQuery>(() => normalizeGroupsQuery(route.query))
  /** Update query parameters and push to router */
  const updateQuery = async (newQuery: Partial<GroupsSearchQuery>) => {
    await navigateTo({
      query: {
        ...route.query,
        ...newQuery,
      },
    })
  }

  const searchTerm = ref(query.value.q)
  const sortKey = computed(() => query.value.k)
  const sortOrder = computed(() => query.value.d)
  const pageNumber = ref(query.value.p)
  const pageSize = ref(query.value.l)

  const searchIdentityKey = computed(() => {
    const { k, d, p, l, ...filters } = query.value
    return JSON.stringify(filters)
  })

  const selectedMap = useState<Record<string, boolean>>(
    `selection-groups:${searchIdentityKey.value}`, () => ({}),
  )

  /** Number of selected groups */
  const selectedCount = computed(() => {
    return Object.values(selectedMap.value).filter(value => value === true).length
  })
  const toggleSelection = (event: Event | undefined, row: Row<GroupSummary>) => {
    selectedMap.value[row.id] = !selectedMap.value[row.id]
    row.toggleSelected(selectedMap.value[row.id])
  }

  /** Column names with translations */
  const columnNames = computed<Record<keyof GroupSummary, string>>(() => ({
    id: '#',
    displayName: $t('groups.table.column.display-name'),
    public: $t('groups.table.column.public'),
    memberListVisibility: $t('groups.table.column.member-list-visibility'),
    usersCount: $t('groups.table.column.users-count'),
  }))

  const publicStatus = computed(() => ({
    true: $t('groups.table.cell.public.public'),
    false: $t('groups.table.cell.public.private'),
  }))

  const visibilityStatus = computed(() => ({
    Public: $t('groups.table.cell.visibility.public'),
    Private: $t('groups.table.cell.visibility.private'),
    Hidden: $t('groups.table.cell.visibility.hidden'),
  }))

  /** Returns action buttons for a group entity */
  const creationButtons = computed<ButtonProps[]>(() => [
    {
      icon: 'i-lucide-plus',
      label: $t('button.create-new'),
      to: '/groups/new',
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

  /** Actions for selected groups */
  const selectedGroupsActions = computed<DropdownMenuItem[]>(() => [
    {
      icon: 'i-lucide-trash',
      label: $t('groups.delete-selected-button'),
      onClick: () => {
        // TODO: Delete selected groups
      },
    },
  ])

  type GroupsTableColumn = TableColumn<GroupSummary>
  const columns = computed<GroupsTableColumn[]>(() => [
    {
      id: 'select',
      header: ({ table }) =>
        h(UCheckbox, {
          'modelValue': table.getIsSomePageRowsSelected()
            ? 'indeterminate'
            : table.getIsAllPageRowsSelected(),
          'onUpdate:modelValue': value => table.toggleAllPageRowsSelected(!!value),
          'aria-label': 'Select all',
        }),
      cell: ({ row }) =>
        h(UCheckbox, {
          'modelValue': row.getIsSelected(),
          'onUpdate:modelValue': () => toggleSelection(undefined, row),
          'aria-label': 'Select row',
        }),
      enableHiding: false,
    },
    {
      accessorKey: 'id',
      header: () => sortableHeader('id'),
    },
    {
      accessorKey: 'displayName',
      header: () => sortableHeader('displayName'),
      cell: ({ row }) => {
        const name: string = row.original.displayName
        return h(ULink, {
          to: `/groups/${row.original.id}`,
          class: 'font-bold hover:underline inline-flex items-center',
        }, [
          h('span', name),
        ])
      },
      enableHiding: false,
    },
    {
      accessorKey: 'public',
      header: () => sortableHeader('public'),
      cell: ({ row }) => (
        publicStatus.value[`${row.original.public}`]
      ),
    },
    {
      accessorKey: 'memberListVisibility',
      header: () => sortableHeader('memberListVisibility'),
      cell: ({ row }) => (
        visibilityStatus.value[row.original.memberListVisibility]
      ),
    },
    {
      accessorKey: 'usersCount',
      header: () => h(
        'span', { class: 'text-xs text-default font-medium' }, columnNames.value.usersCount,
      ),
      cell: ({ row }) => row.original.usersCount,
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
  ],
  )

  function sortableHeader(key: GroupsSortableKeys) {
    const label = columnNames.value[key]
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

  function getActionItems(row: TableRow<GroupSummary>): DropdownMenuItem[] {
    return [
      {
        type: 'label',
        label: $t('table.actions-label'),
      },
      {
        label: $t('groups.actions.copy-id'),
        onSelect() {
          copy(row.original.id)

          toast.add({
            title: $t('toast.success.title'),
            description: $t('toast.success.copy-group-id.description'),
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
        to: `/groups/${row.original.id}`,
        icon: 'i-lucide-eye',
      },
      {
        label: $t('table.actions.delete'),
        onSelect: () => {},
        icon: 'i-lucide-trash',
        color: 'error',
      },
    ]
  }

  const columnVisibility = ref({ id: false })

  const makeAttributeFilters = (data: Ref<FilterOption[] | undefined>) => {
    const options = computed(() => (
      Object.fromEntries(data.value?.map(option => [option.key, option]) ?? [],
      ) as Record<keyof GroupsSearchQuery, FilterOption>
    ))

    const filters = computed(() => [
      {
        key: 'r',
        placeholder: $t('repositories.title'),
        icon: 'i-lucide-folder',
        items: options.value.r.items ?? [],
        multiple: options.value.r.multiple ?? false,
        searchInput: true,
        onUpdated: (values: unknown) => {
          updateQuery({ r: (values as { value: string }[]).map(v => v.value), p: 1 })
        },
      },
      {
        key: 's',
        placeholder: $t('groups.table.column.public'),
        icon: '',
        items: options.value.s.items?.map(item => ({
          value: item.value,
          label: publicStatus.value[(item.value as 0 | 1 | undefined) === 0 ? 'true' : 'false'],
        })) ?? [],
        multiple: options.value.s.multiple ?? false,
        searchInput: false,
        onUpdated: (values: unknown) => {
          updateQuery({ s: (values as { value: 0 | 1 | undefined }).value, p: 1 })
        },
      },
      {
        key: 'v',
        placeholder: $t('groups.table.column.member-list-visibility'),
        icon: '',
        items: options.value.v.items?.map((item) => {
          const v = (item.value as 0 | 1 | 2 | undefined) === 0
            ? 'Public'
            : (item.value === 1 ? 'Private' : 'Hidden')

          return {
            value: item.value,
            label: visibilityStatus.value[v] }
        }) ?? [],
        multiple: options.value.v.multiple ?? false,
        searchInput: false,
        onUpdated: (values: unknown) => {
          updateQuery({ v: (values as { value: 0 | 1 | 2 | undefined }).value, p: 1 })
        },
      },
    ])

    return filters
  }

  const makePageInfo = (result: Ref<GroupsSearchResult | undefined>) => {
    return computed(() => {
      const start = result.value?.offset ?? 1
      const total = result.value?.total ?? 0
      const end = Math.min(start + pageSize.value!, total)
      const count = selectedCount.value

      if (count > 0)
        return `${start} - ${end} / ${total} (${$t('table.selected')} ${count})`
      return `${start} - ${end} / ${total}`
    })
  }

  return {
    query,
    updateQuery,
    criteria: {
      searchTerm,
      sortKey,
      sortOrder,
      pageNumber,
      pageSize,
    },
    columnNames,
    selectedMap,
    selectedCount,
    toggleSelection,
    selectedGroupsActions,
    creationButtons,
    emptyActions,
    columns,
    columnVisibility,
    makeAttributeFilters,
    makePageInfo,
  }
}

export { useGroupsTable }
