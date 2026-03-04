<script setup lang="ts">
import type { TabsItem } from '@nuxt/ui'

const {
  query, makePageInfo, updateQuery,
  tab, uploadColumns, downloadColumns, isFileAvailable,
} = useHistory()

const childData = ref<DownloadApiModel>()

const tabItems = computed<TabsItem[]>(() => [
  { label: $t('history.tab.download'), icon: 'i-lucide-download', slot: 'download',
    value: 'download' },
  { label: $t('history.tab.upload'), icon: 'i-lucide-upload', slot: 'upload', value: 'upload' },
])

const { handleFetchError } = useErrorHandling()
const { data, execute } = useFetch<DownloadApiModel | UploadApiModel>(`/api/history/${tab.value}`, {
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
    execute()
  },
})

const toggleSort = () => {
  updateQuery({ d: query.value.d === 'asc' ? 'desc' : 'asc' })
}

const handleLoadMoreChildren = async (row: DownloadHistoryData) => {
  const { data } = await useFetch<DownloadApiModel>('/api/history/download', {
    method: 'GET',
    query: {
      i: [row.id],
    },
    onResponseError({ response }) {
      switch (response.status) {
        case 400: {
          showError({
            status: 400,
            statusText: 'Bad Request',
            message: $t('error-page.failed.load-more'),
          })
          break
        }
        default:{
          handleFetchError({ response })
          break
        }
      }
    },
  })
  childData.value = data.value
}
</script>

<template>
  <UPageHeader
    :title="$t('history.title')"
    :description="$t('history.description')"
    :ui="{ root: 'py-2', description: 'mt-2' }"
  />
  <UTabs
    v-model="activeTab"
    :items="tabItems"
    class="w-full"
    variant="link"
    :ui="{ trigger: 'min-w-50' }"
  >
    <template #download>
      <div class="container mx-auto px-4">
        <HistoryFilter target="download" />

        <div>
          <HistoryTable
            key="download-table" :data="(data?.resources ?? []) as DownloadHistoryData[]"
            :total="data?.total ?? 0"
            :table-config="{ enableExpand: true, showStatus: false }"
            :file-availability-check="isFileAvailable"
            :page-info="pageInfo" :offset="offset"
            :child-data="childData?.resources ?? []"
            :columns="downloadColumns"
            @sort-change="toggleSort"
            @load-more-children="handleLoadMoreChildren"
          />
        </div>
      </div>
    </template>

    <template #upload>
      <div class="container mx-auto px-4">
        <HistoryFilter target="upload" />

        <div>
          <HistoryTable
            key="upload-table" :data="(data?.resources ?? []) as UploadHistoryData[]"
            :total="data?.total ?? 0"
            :table-config="{ enableExpand: false, showStatus: true }"
            :page-info="pageInfo" :offset="offset"
            :columns="uploadColumns"
            @sort-change="toggleSort"
          />
        </div>
      </div>
    </template>
  </UTabs>
</template>
