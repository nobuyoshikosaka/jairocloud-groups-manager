<script setup lang="ts" generic="T extends DownloadHistoryData | UploadHistoryData">
import type { TableColumn } from '@nuxt/ui'

interface Properties<T> {
  data: T[]
  total: number
  tableConfig?: {
    enableExpand?: boolean
    showStatus?: boolean
  }
  columns: TableColumn<T, unknown>[]
  pageInfo: string
  offset: number
  fileAvailabilityCheck?: (data: DownloadHistoryData) => boolean
}
defineProps<Properties<T>>()

const { pageSize, pageNumber, updateQuery } = useHistory()
const { table: { pageSize: { history: pageOptions } } } = useAppConfig()
</script>

<template>
  <div class="flex items-center justify-between">
    <h2 class="text-xl font-semibold">
      {{ $t('history.table-title') }}
    </h2>
    <div class="flex items-center gap-2">
      <label class="text-sm text-gray-600 mr-1">{{ $t('table.page-size-label') }}</label>
      <USelect
        v-model="pageSize" :items="pageOptions"
        class="w-24"
        @update:model-value="() => updateQuery(
          { l: pageSize, p: Math.ceil(offset / pageSize!) },
        )"
      />
    </div>
  </div>

  <UTable
    :data="data"
    :columns="columns"
    row-key="id"
    :loading="false"
  >
    <template #empty>
      <UEmpty
        icon="i-lucide-search-x"
        :title="$t('history.empty-data')"
      />
    </template>
  </UTable>

  <div class="grid grid-cols-3 items-center">
    <div class="flex-1 text-gray-500 text-sm">
      {{ pageInfo }}
    </div>
    <div class="flex justify-center">
      <UPagination
        v-model:page="pageNumber"
        :items-per-page="pageSize"
        :total="total"
        @update:page="(value) => updateQuery({ p: value })"
      />
    </div>
  </div>
</template>
