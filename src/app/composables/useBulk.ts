/**
 * Composable for bulk user upload operations
 */
import { UBadge, UIcon } from '#components'

import type { FetchError } from 'ofetch'
import type { BadgeProps, TableColumn } from '@nuxt/ui'

const toast = useToast()

const useBulk = <T extends UploadResult | ValidationResult>() => {
  const currentStep = ref<'upload' | 'validate' | 'result'>('upload')

  const { t: $t } = useI18n()
  const items = computed(() => [
    {
      title: $t('bulk.step.select_file'),
      description: $t('bulk.step.select_file_description'),
      value: 'upload',
      icon: 'i-lucide-file-up',
    },
    {
      title: $t('bulk.step.validate'),
      description: $t('bulk.step.validate_description'),
      value: 'validate',
      icon: 'i-lucide-shield-check',
    },
    {
      title: $t('bulk.step.complete'),
      description: $t('bulk.step.complete_description'),
      value: 'result',
      icon: 'i-lucide-circle-check-big',
    },
  ])

  const route = useRoute()
  const query = computed<UploadQuery>(() => normalizeUploadQuery(route.query))
  const updateQuery = async (newQuery: Partial<UploadQuery>) => {
    await navigateTo({
      query: {
        ...route.query,
        ...newQuery,
      },
    })
  }
  const pageSize = ref(query.value.l)
  const pageNumber = ref(query.value.p)
  const sortOrder = ref(query.value.d)
  const makePageInfo = (result: Ref<ResultSummary | undefined>) => {
    return computed(() => {
      const start = result.value?.offset ?? 1
      const total = result.value?.total ?? 0
      const end = Math.min(start + pageSize.value!, total)
      return `${start} - ${end} / ${total}`
    })
  }

  const makeStatusFilters = () => {
    const filterOptions: { label: string, value: StatusType }[] = [
      { label: $t('bulk.status.create'), value: 'create' },
      { label: $t('bulk.status.delete'), value: 'delete' },
      { label: $t('bulk.status.error'), value: 'error' },
      { label: $t('bulk.status.skip'), value: 'skip' },
      { label: $t('bulk.status.update'), value: 'update' },
    ]

    const filters = computed(() => [
      {
        key: 'f',
        items: filterOptions ?? [],
        multiple: true,
        onUpdated: (values: unknown) => {
          const selectedValues = (values as { value: StatusType }[]).map(v => v.value)
          updateQuery({ f: selectedValues.map(String), p: 1 })
        },
      },
    ])
    return filters
  }

  const STATUS_CONFIG = computed<{ [key in StatusType]: BadgeProps }>(() => ({
    create: { color: 'success', label: $t('bulk.status.create'), icon: 'i-lucide-plus-circle' },
    update: { color: 'info', label: $t('bulk.status.update'), icon: 'i-lucide-pencil' },
    delete: { color: 'error', label: $t('bulk.status.delete'), icon: 'i-lucide-trash-2' },
    skip: { color: 'neutral', label: $t('bulk.status.skip'), icon: 'i-lucide-minus-circle' },
    error: { color: 'error', label: $t('bulk.status.error'), icon: 'i-lucide-circle-x' },
  }))

  const columns = computed<TableColumn<T>[]>(() => [
    {
      accessorKey: 'row',
      header: $t('bulk.column.row'),
      cell: ({ row }) => {
        const rowNumber = row.getValue('row')
        return rowNumber ? `${rowNumber}` : '-'
      },
      meta: { class: { td: 'w-20' } },
    },
    {
      accessorKey: 'userName',
      header: $t('bulk.column.user-name'),
      cell: ({ row }) => {
        const name = row.getValue('userName') as string
        return name || h('span', { class: 'text-muted italic' }, $t('bulk.empty'))
      },
    },
    {
      accessorKey: 'eppn',
      header: $t('bulk.column.eppn'),
      cell: ({ row }) => {
        const eppn = row.getValue('eppn') as string | string[]
        const eppnArray = Array.isArray(eppn) ? eppn : [eppn]
        return eppnArray && eppnArray.length > 0
          ? h('div', { class: 'flex flex-col gap-1' },
              eppnArray.map(eppns => h('span', { class: 'font-mono text-sm' }, eppns)))
          : h('span', { class: 'text-muted italic' }, $t('bulk.empty'))
      },
    },
    {
      accessorKey: 'groups',
      header: $t('bulk.column.groups'),
      cell: ({ row }) => {
        const groups = row.getValue('groups') as string[]
        return groups && groups.length > 0
          ? h('div', { class: 'flex flex-col gap-1' },
              groups.map(group => h('span', { class: 'font-mono text-sm' }, group)))
          : h('span', { class: 'text-muted italic' }, $t('bulk.empty'))
      },
    },
    {
      accessorKey: 'status',
      header: $t('bulk.column.status'),
      cell: ({ row }) => {
        const data = row.original
        const status = data.status
        const message = data.code

        const badgeConfig = STATUS_CONFIG.value[status]

        return h('div', { class: 'flex items-center gap-2' }, [
          h(UBadge, { color: badgeConfig.color, variant: 'subtle', class: 'gap-1' }, () => [
            h(UIcon, { name: badgeConfig.icon, class: 'size-3' }),
            badgeConfig.label,
          ]),
          message
            ? h('span', { class: 'text-sm text-muted' }, message)
            : undefined,
        ].filter(Boolean))
      },
    },
  ])

  return {
    query,
    currentStep,
    items,
    pageSize,
    pageNumber,
    sortOrder,
    STATUS_CONFIG,
    columns,
    makePageInfo,
    updateQuery,
    makeStatusFilters,
  }
}

const useUserUpload = () => {
  const selectedFile = ref<File | undefined>(undefined)
  const isProcessing = ref<boolean>(false)

  return {
    selectedFile,
    isProcessing,
  }
}

const useValidation = ({ taskId, selectedRepository }: { taskId: Ref<string | undefined>
  selectedRepository: Ref<string | undefined> }) => {
  const { query } = useBulk()
  const validationResults = ref<ValidationResult[]>([])
  const missingUsers = ref<MissingUser[]>([])

  const selectedMissingUsers = useState<Record<string, boolean>>(
    `selection-missing-users:${taskId}`, () => ({}),
  )
  const fetchValidationResults = (url: string) => {
    return useFetch<ResultSummary>(url, {
      method: 'GET',
      query,
      lazy: true,
      server: false,
      onResponseError({ response }) {
        switch (response.status) {
          case 400: { {
            toast.add({
              title: $t('bulk.status.error'),
              description: $t('bulk.validation.fetch_failed'),
              color: 'error',
              icon: 'i-lucide-circle-x',
            }) }
          break
          }
          default:{
            handleFetchError({ response })
            break
          }
        }
      },
    })
  }
  const selectedCount = computed(() => {
    return Object.values(selectedMissingUsers.value).filter(value => value === true).length
  })
  const toggleSelection = (userId: string) => {
    selectedMissingUsers.value[userId] = !selectedMissingUsers.value[userId]
  }
  const temporaryFileId = ref<string | undefined>(undefined)
  const summary = ref({
    create: 0, update: 0, delete: 0, skip: 0, error: 0,
  })

  const { handleFetchError } = useErrorHandling()
  const executeBulkUpdate = async (url: string) => {
    if (!taskId || !selectedRepository.value) {
      throw new Error('Missing required data')
    }
    try {
      const results = await $fetch<BulkProcessingStatus>(url, {
        method: 'POST',
        body: {
          taskId: taskId.value,
          tempFileId: temporaryFileId.value,
          repositoryId: selectedRepository.value,
          deleteUsers:
          Object.keys(selectedMissingUsers.value).filter(key => selectedMissingUsers.value[key]),
        } as ExcuteRequest,
      })
      return results
    }
    catch (error) {
      handleFetchError({ response: (error as FetchError).response! })
      return { taskId: undefined, historyId: undefined }
    }
  }

  const useBulkIndicators = computed<BulkIndicator[]>(() => [
    {
      title: $t('bulk.status.create'),
      icon: 'i-lucide-plus-circle',
      number: summary.value.create ?? 0,
      color: 'success',
      key: 'create',
    },
    {
      title: $t('bulk.status.update'),
      icon: 'i-lucide-pencil',
      number: summary.value.update ?? 0,
      color: 'info',
      key: 'update',
    },
    {
      title: $t('bulk.status.delete'),
      icon: 'i-lucide-trash-2',
      number: summary.value.delete ?? 0,
      color: 'error',
      key: 'delete',
    },
    {
      title: $t('bulk.status.skip'),
      icon: 'i-lucide-minus-circle',
      number: summary.value.skip ?? 0,
      color: 'warning',
      key: 'skip',
    },
    {
      title: $t('bulk.status.error'),
      icon: 'i-lucide-circle-x',
      number: summary.value.error ?? 0,
      color: 'error',
      key: 'error',
    },
  ])

  return {
    useBulkIndicators,
    query,
    validationResults,
    missingUsers,
    selectedMissingUsers,
    selectedCount,
    summary,
    taskId,
    temporaryFileId,
    fetchValidationResults,
    executeBulkUpdate,
    toggleSelection,
  }
}

const useExecuteUpload = () => {
  const { query } = useBulk()
  const uploadResult = ref<ResultSummary | undefined>(undefined)
  const { handleFetchError } = useErrorHandling()
  const fetchUploadResult = async (url: string) => {
    const { data, execute } = await useFetch<ResultSummary>(url, {
      method: 'GET',
      query,
      lazy: true,
      server: false,
      onResponseError({ response }) {
        switch (response.status) {
          case 400: {
            toast.add({
              title: $t('bulk.status.error'),
              description: $t('bulk.execute.result_failed'),
              color: 'error',
              icon: 'i-lucide-circle-x',
            })
            break
          }
          default: {
            handleFetchError({ response })
            break
          }
        }
      },
    })
    return { uploadResult: data, execute }
  }

  const resultSummary = computed(() => ({
    create: uploadResult.value!.summary.create,
    update: uploadResult.value!.summary.update,
    delete: uploadResult.value!.summary.delete,
    skip: uploadResult.value!.summary.skip,
    error: uploadResult.value!.summary.error,
  }))

  const useBulkIndicators = computed<BulkIndicator[]>(() => [
    {
      title: $t('bulk.status.create'),
      icon: 'i-lucide-plus-circle',
      number: resultSummary.value.create ?? 0,
      color: 'success',
      key: 'create',
    },
    {
      title: $t('bulk.status.update'),
      icon: 'i-lucide-pencil',
      number: resultSummary.value.update ?? 0,
      color: 'info',
      key: 'update',
    },
    {
      title: $t('bulk.status.delete'),
      icon: 'i-lucide-trash-2',
      number: resultSummary.value.delete ?? 0,
      color: 'error',
      key: 'delete',
    },
    {
      title: $t('bulk.status.skip'),
      icon: 'i-lucide-minus-circle',
      number: resultSummary.value.skip ?? 0,
      color: 'warning',
      key: 'skip',
    },
    {
      title: $t('bulk.status.error'),
      icon: 'i-lucide-circle-x',
      number: resultSummary.value.error ?? 0,
      color: 'error',
      key: 'error',
    },
  ])
  return {
    uploadResult,
    useBulkIndicators,
    fetchUploadResult,
    resultSummary,
  }
}
export { useBulk, useUserUpload, useValidation, useExecuteUpload }
