<script setup lang="ts">
import { useI18n, useRoute, useRouter } from '#imports'

import type { TabsItem } from '@nuxt/ui'

const { t: $t } = useI18n()
const route = useRoute()
const router = useRouter()

const downloadHistory = useHistory('download')
const uploadHistory = useHistory('upload')

const currentHistory = computed(() =>
  activeTab.value === 'download' ? downloadHistory : uploadHistory,
)

const tabItems = computed<TabsItem>(() => [
  { label: $t('history.tub', 1), icon: 'i-lucide-download', slot: 'download', value: 'download' },
  { label: $t('history.tub', 2), icon: 'i-lucide-upload', slot: 'upload', value: 'upload' },
])

const activeTab = computed<string>({
  get() {
    return (route.query.tab as string) || 'download'
  },
  set(tab) {
    router.push({ path: '/history', query: { ...route.query, tab } })
  },
})

function toPositiveInt(v: unknown, fallback: number) {
  if (!Number.isFinite(fallback) || fallback === undefined) fallback = 1
  if (v === undefined) return fallback
  const raw = Array.isArray(v) ? v[0] : v
  let n: number
  if (typeof raw === 'number') n = raw
  else if (typeof raw === 'string') n = Number.parseInt(raw, 10)
  else n = Number(raw)
  return Number.isFinite(n) && Number.isInteger(n) && n > 0 ? n : fallback
}

const currentPage = ref<number>(toPositiveInt(route.query.p, 1))
const itemsPerPage = ref<number>(toPositiveInt(route.query.l, 10))

watch([currentPage, itemsPerPage], () => {
  const qp = toPositiveInt(route.query.p, 1)
  const ql = toPositiveInt(route.query.l, 10)
  if (qp === currentPage.value && ql === itemsPerPage.value) return
  router.replace({
    path: '/history',
    query: { ...route.query, p: currentPage.value, l: itemsPerPage.value },
  })
})

const sortDirection = ref<'asc' | 'desc'>('desc')
onMounted(() => {
  const d = (route.query.d as string) || (route.query.dir as string)
  if (d === 'asc' || d === 'desc') sortDirection.value = d
})

function toggleSort() {
  sortDirection.value = sortDirection.value === 'asc' ? 'desc' : 'asc'
  router.push({ path: '/history', query: { ...route.query, d: sortDirection.value, p: 1 } })
}

watch(
  [
    () => route.query.tab,
    () => route.query.s,
    () => route.query.e,
    () => route.query.o,
    () => route.query.r,
    () => route.query.g,
    () => route.query.u,
    currentPage,
    itemsPerPage,
    sortDirection,
  ],
  () => {
    currentHistory.value.fetchHistory(
      currentPage.value,
      itemsPerPage.value,
      sortDirection.value,
    )
  },
  { immediate: true },
)

const CHILD_PAGE_SIZE = 20
async function handleLoadMoreChildren(parentId: string, currentShown: number) {
  await currentHistory.value.loadChildren(
    parentId,
    currentShown,
    CHILD_PAGE_SIZE,
    currentPage.value,
    itemsPerPage.value,
    sortDirection.value,
  )
}

async function handleAction(action: string, row: ActionRow) {
  const isDownload = 'parent' in row
  const data = isDownload ? row.parent : row

  switch (action) {
    case 'toggle-public': {
      try {
        const result = await currentHistory.value.togglePublicStatus(
          data.id,
          data.public,
        )
        if (result !== undefined) {
          data.public = result
        }
      }
      catch (error_: unknown) {
        currentHistory.value.error.value = error_ instanceof Error
          ? error_.message
          : 'Failed to update status'
      }
      break
    }
    case 'redownload': {
      if (data.file_id) {
        const url = `/api/history/files/${data.file_id}`
        window.open(url, '_blank')
      }
      break
    }
    case 'show-detail': {
      router.push({ path: `/bulk/${data.id}` })
      break
    }
  }
}

const sum = computed(() => currentHistory.value.stats.value.sum ?? 0)
const firstDownload = computed(() => currentHistory.value.stats.value.firstDownload ?? 0)
const reDownload = computed(() => currentHistory.value.stats.value.reDownload ?? 0)
const success = computed(() => currentHistory.value.stats.value.success ?? 0)
const failed = computed(() => currentHistory.value.stats.value.error ?? 0)
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
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <NumberIndicator
            icon="i-lucide-download" :title="$t('history.sum', 1)"
            :number="sum" color="primary"
          />
          <NumberIndicator
            icon="i-lucide-file-check" :title="$t('history.first-download')"
            :number="firstDownload" color="primary"
          />
          <NumberIndicator
            icon="i-lucide-refresh-cw" :title="$t('history.re-download')"
            :number="reDownload" color="secondary"
          />
        </div>

        <HistoryFilter target="download" />

        <div v-if="downloadHistory.loading.value" class="text-center text-sm text-muted py-10">
          {{ $t('common.loading') }}
        </div>
        <div v-else-if="downloadHistory.error.value" class="text-center text-sm text-error  py-10">
          {{ downloadHistory.error.value }}
        </div>
        <div v-else>
          <HistoryTable
            key="download-table"
            v-model:current-page="currentPage"
            v-model:items-per-page="itemsPerPage"
            :data="downloadHistory.downloadGroups.value"
            :total-items="downloadHistory.totalItems.value"
            :table-config="{ enableExpand: true, showStatus: false }"
            :file-availability-check="downloadHistory.isFileAvailable"
            @action="handleAction"
            @sort-change="toggleSort"
            @load-more-children="handleLoadMoreChildren"
          />
        </div>
      </div>
    </template>

    <template #upload>
      <div class="container mx-auto px-4">
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
          <NumberIndicator
            icon="i-lucide-upload" :title="$t('history.sum', 2)"
            :number="sum" color="primary"
          />
          <NumberIndicator
            icon="i-lucide-check-circle" :title="$t('history.success-count')"
            :number="success" color="primary"
          />
          <NumberIndicator
            icon="i-lucide-x-circle" :title="$t('history.failed-count')"
            :number="failed" color="error"
          />
        </div>

        <HistoryFilter target="upload" />

        <div v-if="uploadHistory.loading.value" class="text-center text-sm text-muted py-10">
          {{ $t('common.loading') }}
        </div>
        <div v-else-if="uploadHistory.error.value" class="text-center text-sm text-error  py-10">
          {{ uploadHistory.error.value }}
        </div>
        <div v-else>
          <HistoryTable
            key="upload-table"
            v-model:current-page="currentPage"
            v-model:items-per-page="itemsPerPage"
            :data="uploadHistory.uploadRows.value"
            :total-items="uploadHistory.totalItems.value"
            :table-config="{ enableExpand: false, showStatus: true }"
            :file-availability-check="uploadHistory.isFileAvailable"
            @action="handleAction"
            @sort-change="toggleSort"
          />
        </div>
      </div>
    </template>
  </UTabs>
</template>
