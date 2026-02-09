import { getLocalTimeZone, parseDate } from '@internationalized/date'

import type { CalendarDate } from '@internationalized/date'

interface HistoryFilterOptions {
  target: 'download' | 'upload'
}

function useHistoryFilter(options: HistoryFilterOptions) {
  const route = useRoute()
  const { t: $t } = useI18n()

  const query = computed<HistoryQuery>(() => normalizeHistoryQuery(route.query))
  const updateQuery = async (newQuery: Partial<HistoryQuery>) => {
    await navigateTo({
      query: {
        ...route.query,
        ...newQuery,
      },
    })
  }
  const specifiedIds = ref(query.value.i)
  const specifiedRepos = ref(query.value.r)
  const specifiedGroups = ref(query.value.g)
  const specifiedUsers = ref(query.value.u)
  const specifiedOperators = ref(query.value.o)
  const startDate = ref(query.value.s)
  const endDate = ref(query.value.e)
  const sortOrder = computed(() => query.value.d)
  const pageNumber = ref(query.value.p)
  const pageSize = ref(query.value.l)

  const makeAttributeFilters = (data: Ref<FilterOption[] | undefined>) => {
    const options = computed(() => (
      Object.fromEntries(data.value?.map(option => [option.key, option]) ?? [],
      ) as Record<keyof HistoryQuery, FilterOption>
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
        key: 'g',
        placeholder: $t('groups.title'),
        icon: 'i-lucide-shield-check',
        items: options.value.g.items ?? [],
        multiple: options.value.g.multiple ?? false,
        searchInput: true,
        onUpdated: (values: unknown) => {
          updateQuery({ g: (values as { value: string }[]).map(v => v.value), p: 1 })
        },
      },
      {
        key: 'u',
        placeholder: $t('users.title'),
        icon: 'i-lucide-users',
        items: options.value.u.items ?? [],
        multiple: options.value.u.multiple ?? false,
        searchInput: true,
        onUpdated: (values: unknown) => {
          updateQuery({ u: (values as { value: string }[]).map(v => v.value), p: 1 })
        },
      },
      {
        key: 'o',
        placeholder: $t('history.operator'),
        icon: 'i-lucide-user-check',
        items: options.value.o.items ?? [],
        multiple: options.value.o.multiple ?? false,
        searchInput: true,
        onUpdated: (values: unknown) => {
          updateQuery({ o: (values as { value: string }[]).map(v => v.value), p: 1 })
        },
      },
    ])

    return filters
  }
  const dateRange = shallowRef<{ start: CalendarDate | undefined, end: CalendarDate | undefined }>({
    start: startDate.value ? parseDate(startDate.value) : undefined,
    end: endDate.value ? parseDate(endDate.value) : undefined,
  })

  const formattedDateRange = computed(() => {
    if (!dateRange.value.start) return $t('users.table.column.last-modified')
    const from = dateFormatter.format(dateRange.value.start.toDate(getLocalTimeZone()))
    const to = dateRange.value.end
      ? dateFormatter.format(dateRange.value.end.toDate(getLocalTimeZone()))
      : undefined

    return to ? `${from} - ${to}` : from
  })

  const targetLabel = computed(() =>
    options.target === 'download' ? $t('history.target', 1) : $t('history.target', 2),
  )

  return {
    query,
    updateQuery,
    criteria: {
      specifiedIds,
      specifiedRepos,
      specifiedGroups,
      specifiedUsers,
      specifiedOperators,
      startDate,
      endDate,
      sortOrder,
      pageNumber,
      pageSize,
    },
    dateFilter: {
      dateRange,
      formattedDateRange,
    },
    targetLabel,
    makeAttributeFilters,
  }
}

function useHistoryFilterOptions(target: Ref<'download' | 'upload'>) {
  const operatorOptions = ref<SelectOption[]>([])
  const repoOptions = ref<SelectOption[]>([])
  const groupOptions = ref<SelectOption[]>([])
  const userOptions = ref<SelectOption[]>([])

  const loading = ref(false)
  const error = ref<string | undefined>(undefined)

  async function loadOptions() {
    if (loading.value) return

    loading.value = true
    error.value = undefined

    try {
      const payload = await $fetch<FilterOptionsResponse>(
        `/api/history/${target.value}/filter-options`,
        { method: 'GET' },
      )

      if (!payload) throw new Error('Empty filter options')

      operatorOptions.value = (payload.operators ?? []).map(o => ({
        label: o.user_name ?? o.id,
        value: o.id,
      }))

      repoOptions.value = (payload.target_repositories ?? []).map(r => ({
        label: r.display_name ?? r.id,
        value: r.id,
      }))

      groupOptions.value = (payload.target_groups ?? []).map(g => ({
        label: g.display_name ?? g.id,
        value: g.id,
      }))

      userOptions.value = (payload.target_users ?? []).map(u => ({
        label: u.user_name ?? u.id,
        value: u.id,
      }))
    }
    catch {
      error.value = 'Failed to load filter options.'
    }
    finally {
      loading.value = false
    }
  }

  return {
    operatorOptions,
    repoOptions,
    groupOptions,
    userOptions,
    loading,
    error,
    loadOptions,
  }
}
function computeEffectiveTotal(itemsLength: number, currentPage: number,
  itemsPerPage: number): number {
  const base = (currentPage - 1) * itemsPerPage + itemsLength
  return base + (itemsPerPage === itemsLength ? 1 : 0)
}

function useHistory(target: 'download' | 'upload') {
  const route = useRoute()

  const query = computed<HistoryQuery>(() => normalizeHistoryQuery(route.query))
  const updateQuery = async (newQuery: Partial<HistoryQuery>) => {
    await navigateTo({
      query: {
        ...route.query,
        ...newQuery,
      },
    })
  }
  const loading = ref(false)
  const error = ref<string | undefined>(undefined)
  const downloadGroups = ref<DownloadGroupItem[]>([])
  const uploadRows = ref<UploadHistoryData[]>([])
  const totalItems = ref<number>(0)
  const stats = ref<HistoryStats>({
    sum: 0,
    firstDownload: 0,
    reDownload: 0,
    success: 0,
    error: 0,
  })
  const fileExistsCache = ref<Map<string, boolean>>(new Map())

  async function checkFileExists(fileId: string): Promise<boolean> {
    if (fileExistsCache.value.has(fileId)) {
      return fileExistsCache.value.get(fileId)!
    }

    try {
      const result = await $fetch<boolean>(`/api/history/files/${fileId}/exists`)
      fileExistsCache.value.set(fileId, result)
      return result
    }
    catch {
      fileExistsCache.value.set(fileId, false)
      return false
    }
  }

  async function preloadFileExistence(items: DownloadHistoryData[]) {
    const fileIds = items
      .filter(item => item.file_id)
      .map(item => item.file_id!)

    await Promise.all(fileIds.map(id => checkFileExists(id)))
  }

  function isFileAvailable(data: DownloadHistoryData): boolean {
    if (!data.file_id) return false
    return fileExistsCache.value.get(data.file_id) ?? true
  }

  function buildQueryForApi(
    currentPage: number,
    itemsPerPage: number,
    sortDirection: 'asc' | 'desc',
  ): HistoryQuery {
    const q: HistoryQuery = { ...route.query }
    delete q.tab
    q.p = currentPage
    q.l = itemsPerPage
    q.d = sortDirection
    return q
  }

  async function fetchDownloadHistory(
    currentPage: number,
    itemsPerPage: number,
    sortDirection: 'asc' | 'desc',
  ) {
    const payload = await $fetch<DownloadApiModel | null>('/api/history/download', {
      method: 'GET',
      query: buildQueryForApi(currentPage, itemsPerPage, sortDirection),
    })

    if (!payload) throw new Error('Empty response')

    const list = payload.download_history_data ?? []
    downloadGroups.value = list.map(p => ({
      parent: p,
      children: [],
      hasMoreChildren: (p.children_count ?? 0) > 0,
      childrenLimit: 0,
    }))

    await preloadFileExistence(list)

    const pg = payload.pagination
    totalItems.value = typeof pg?.total === 'number'
      ? Number(pg.total)
      : computeEffectiveTotal(downloadGroups.value.length, currentPage, itemsPerPage)

    if (payload.summary && typeof payload.summary.total === 'number') {
      stats.value.sum = Number(payload.summary.total)
      stats.value.firstDownload = Number(payload.summary.first ?? 0)
      stats.value.reDownload = Number(payload.summary.redownload ?? 0)
    }
    else {
      stats.value.sum = Number(payload.sum_download ?? downloadGroups.value.length)
      stats.value.firstDownload = Number(payload.first_download ?? 0)
      stats.value.reDownload = Number(payload.re_download ?? 0)
    }
    stats.value.success = 0
    stats.value.error = 0
  }

  async function fetchUploadHistory(
    currentPage: number,
    itemsPerPage: number,
    sortDirection: 'asc' | 'desc',
  ) {
    const payload = await $fetch<UploadApiModel | null>('/api/history/upload', {
      method: 'GET',
      query: buildQueryForApi(currentPage, itemsPerPage, sortDirection),
    })

    if (!payload) throw new Error('Empty response')

    const list = payload.upload_history_data ?? []
    uploadRows.value = list.map(row => ({
      ...row,
      users: Array.isArray(row.users) ? row.users : [],
      groups: Array.isArray(row.groups) ? row.groups : [],
    }))

    const pg = payload.pagination
    totalItems.value = typeof pg?.total === 'number'
      ? Number(pg.total)
      : computeEffectiveTotal(uploadRows.value.length, currentPage, itemsPerPage)

    if (payload.summary && typeof payload.summary.total === 'number') {
      stats.value.sum = Number(payload.summary.total)
      stats.value.success = Number(payload.summary.success ?? 0)
      stats.value.error = Number(payload.summary.failed ?? 0)
    }
    else {
      stats.value.sum = Number(payload.sum_upload ?? uploadRows.value.length)
      stats.value.success = Number(payload.success_upload ?? 0)
      stats.value.error = Number(payload.failed_upload ?? 0)
    }
    stats.value.firstDownload = 0
    stats.value.reDownload = 0
  }

  async function fetchHistory(
    currentPage: number,
    itemsPerPage: number,
    sortDirection: 'asc' | 'desc',
  ) {
    loading.value = true
    error.value = undefined

    try {
      await (target === 'download'
        ? fetchDownloadHistory(currentPage, itemsPerPage, sortDirection)
        : fetchUploadHistory(currentPage, itemsPerPage, sortDirection))
    }
    catch (error_: unknown) {
      const message = error_ instanceof Error ? error_.message : String(error_)
      error.value = message
    }
    finally {
      loading.value = false
    }
  }

  async function loadChildren(
    parentId: string,
    offset: number,
    limit: number,
    currentPage: number,
    itemsPerPage: number,
    sortDirection: 'asc' | 'desc',
  ) {
    const payload = await $fetch<DownloadApiModel | null>('/api/history/download', {
      method: 'GET',
      query: {
        ...buildQueryForApi(currentPage, itemsPerPage, sortDirection),
        i: [parentId],
        p: Math.floor(offset / limit) + 1,
        l: limit,
      },
    })

    const items = (payload?.download_history_data ?? []) as DownloadHistoryData[]
    await preloadFileExistence(items)

    const group = downloadGroups.value.find(g => g.parent.id === parentId)
    if (!group) return

    group.children = [...group.children, ...items]
    const totalChildCount = group.parent.children_count ?? group.children.length
    group.hasMoreChildren = group.children.length < totalChildCount
  }

  async function togglePublicStatus(
    id: string,
    currentPublic: boolean,
  ) {
    const body = { public: !currentPublic }
    const result = await $fetch<boolean>(`/api/history/${target}/${id}/public-status`, {
      method: 'PUT',
      body,
    })
    return result
  }

  return {
    loading,
    error,
    downloadGroups,
    uploadRows,
    totalItems,
    stats,
    query,
    updateQuery,
    fetchHistory,
    loadChildren,
    togglePublicStatus,
    isFileAvailable,
  }
}

export { useHistory, useHistoryFilter, useHistoryFilterOptions }
