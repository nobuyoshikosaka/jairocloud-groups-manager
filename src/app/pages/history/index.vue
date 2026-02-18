<script setup lang="ts">
import type { TabsItem } from '@nuxt/ui'

const { t: $t } = useI18n()

const { loading,
  query,
  makePageInfo,
  updateQuery,
  loadChildren,
  togglePublicStatus,
  tab,
  uploadColumns,
  downloadColumns,
  isFileAvailable } = useHistory()

const { features: { history: { upload: fileUpload } } } = useAppConfig()

const tabItems = computed<TabsItem[]>(() => fileUpload
  ? [
      { label: $t('history.tab.download'), icon: 'i-lucide-download', slot: 'download',
        value: 'download' },
      { label: $t('history.tab.upload'), icon: 'i-lucide-upload', slot: 'upload', value: 'upload' },
    ]
  : [
      { label: $t('history.tab.download'), icon: 'i-lucide-download', slot: 'download',
        value: 'download' },
    ])

const { handleFetchError } = useErrorHandling()
const { data } = useFetch<DownloadApiModel | UploadApiModel>(`/api/history/${tab.value}`, {
  method: 'GET',
  query,
  onResponseError: async ({ response }) => {
    handleFetchError({ response })
  },
  lazy: true,
  server: false,
})
const pageInfo = makePageInfo(data)
const offset = computed(() => (data.value?.offset ?? 1))
const activeTab = computed<'download' | 'upload'>({
  get() {
    return (query.value.tab) || 'download'
  },
  set(tab) {
    updateQuery({ tab: tab })
  },
})

const toggleSort = () => {
  updateQuery({ d: query.value.d === 'asc' ? 'desc' : 'asc' })
}

const handleLoadMoreChildren = async (parentId: string) => {
  await loadChildren(parentId)
}

const handleAction = async (action: string, row: ActionRow) => {
  const isDownload = 'parent' in row
  const data = isDownload ? row.parent : row

  switch (action) {
    case 'toggle-public': {
      const result = await togglePublicStatus(
        data.id,
        data.public,
      )
      if (result !== undefined) {
        data.public = result
      }
      break
    }
    case 'redownload': {
      if (data.fileId) {
        const url = `/api/history/files/${data.fileId}`
        window.open(url, '_blank')
      }
      break
    }
    case 'show-detail': {
      navigateTo(`/bulk/${data.id}`)
      break
    }
  }
}
</script>

<template>
  <UPageHeader
    :title="$t('history.title')"
    :description="$t('history.description')"
    :ui="{ root: 'py-2 mb-6', description: 'mt-2' }"
  />
  <UTabs
    v-model="activeTab"
    :items="tabItems"
    class="w-full"
    variant="link"
    :ui="{ trigger: 'min-w-50' }"
  >
    <template #download>
      <div class="container mx-auto px-4  space-y-4">
        <HistoryFilter target="download" />

        <div v-if="loading" class="text-center text-sm text-muted">
          {{ $t('common.loading') }}
        </div>
        <div v-else>
          <HistoryTable
            key="download-table" :data="(data?.resources ?? []) as DownloadHistoryData[]"
            :total="data?.total ?? 0"
            :table-config="{ enableExpand: true, showStatus: false }"
            :file-availability-check="isFileAvailable"
            :page-info="pageInfo" :offset="offset"
            :columns="downloadColumns"
            @sort-change="toggleSort"
            @action="handleAction"
            @load-more-children="handleLoadMoreChildren"
          />
        </div>
      </div>
    </template>

    <template #upload>
      <div class="container mx-auto px-4  space-y-4">
        <HistoryFilter target="upload" />

        <div v-if="loading" class="text-center text-sm text-muted">
          {{ $t('common.loading') }}
        </div>
        <div v-else>
          <HistoryTable
            key="upload-table" :data="(data?.resources ?? []) as UploadHistoryData[]"
            :total="data?.total ?? 0"
            :table-config="{ enableExpand: false, showStatus: true }"
            :file-availability-check="isFileAvailable"
            :page-info="pageInfo" :offset="offset"
            :columns="uploadColumns"
            @action="handleAction"
            @sort-change="toggleSort"
          />
        </div>
      </div>
    </template>
  </UTabs>
</template>
