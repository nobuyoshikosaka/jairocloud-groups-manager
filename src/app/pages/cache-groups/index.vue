<script setup lang="ts">
import { UCheckbox } from '#components'

import type { Row } from '@tanstack/table-core'
import type { SelectItem, TableColumn } from '@nuxt/ui'

const { groupCache: config } = useAppConfig()
const {
  query, updateQuery, criteria, selectedMap, columns,
} = useCacheGroups()

const { searchTerm, filter, pageSize } = criteria

const { table: { pageSize: { cacheGroups: pageOptions } } } = useAppConfig()

const filterItems = ref<SelectItem[]>([
  { label: $t('cache-groups.select.cache'), value: 'cache' },
  { label: $t('cache-groups.select.no-cache'), value: 'no_cache' },
])

const toggleSelection = (row: Row<CacheGroupsSummary>) => {
  selectedMap.value[row.id] = !selectedMap.value[row.id]
  row.toggleSelected(selectedMap.value[row.id])
}
const tableColumns = computed<TableColumn<CacheGroupsSummary>[]>(() => [
  {
    id: 'select',
    header: ({ table }) =>
      h(UCheckbox, {
        'modelValue': table.getIsSomePageRowsSelected()
          ? 'indeterminate'
          : table.getIsAllPageRowsSelected(),
        'onUpdate:modelValue': (value: boolean | 'indeterminate') => {
          table.toggleAllPageRowsSelected(!!value)
          onAllRowsSelected(!!value, table.getRowModel().rows)
        },
        'disabled': isUpdating.value,
        'aria-label': 'Select all',
      }),
    cell: ({ row }) =>
      h(UCheckbox, {
        'modelValue': selectedRows.value.some(selectedRow =>
          selectedRow.original.id === row.original.id,
        ),
        'onUpdate:modelValue': (value: boolean | 'indeterminate') => {
          toggleSelection(row)
          onRowSelected(row, !!value)
        },
        'disabled': isUpdating.value,
        'aria-label': 'Select row',
      }),
    enableHiding: false,
  },
  ...columns.value,
])

/** Selection */
const selectedRows = ref<Row<CacheGroupsSummary>[]>([])
const selectedCount = computed(() => selectedRows.value.length)
function onRowSelected(row: Row<CacheGroupsSummary>, isSelected: boolean) {
  if (isSelected) {
    selectedRows.value.push(row)
  }
  else {
    selectedRows.value = selectedRows.value.filter(r => r.original.id !== row.original.id)
  }
}
function onAllRowsSelected(isSelected: boolean, data: Row<CacheGroupsSummary>[]) {
  selectedRows.value = isSelected ? data : []
}

/** Selected Modal */
const selectedModalTitle = ref('')
const onClickSelectRepositories = () => {
  const count = selectedRows.value.length
  selectedModalTitle.value
    = $t('cache-groups.confirm-update-selected-repositories', { count }) as string
}

/** All Modal */
const allModalTitle = ref('')
const totalCount = ref(0)
const onClickAllRepositories = () => {
  allModalTitle.value
    = $t('cache-groups.confirm-update-all-repositories', { count: totalCount.value }) as string
}

/** Update Progress */
const isUpdating = ref(false)
const progress = ref(0)
const progressCount = ref('')

const { data } = await useFetch<CacheGroupSearchResult>(
  '/api/cache-groups/', {
    method: 'get',
    query,
    lazy: true,
    server: false,
    onResponseError() {
      data.value = { resources: [], total: 0, pageSize: 0, offset: 0 }
    },
  })

const updateCaches = (close: () => void, op: string) => {
  close()
  progress.value = 0
  $fetch('/api/cache-groups/', {
    method: 'post',
    body: {
      fqdnList: selectedRows.value,
      op: op,
    },
  }).then(async () => {
    isUpdating.value = true
    await checkProgress()
  }).catch(() => {
    const toast = useToast()
    toast.add({
      title: $t('cache-groups.update-error') as string,
      color: 'error',
      icon: 'i-lucide-x-circle',
    })
  })
}

async function checkProgress() {
  if (!isUpdating.value) return

  const result = ref<CacheGroupsUpdateResult[]>([])
  while (isUpdating) {
    $fetch('/api/cache-groups/task', {
      method: 'get',
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      onResponse(response: any) {
        const taskDetail: TaskDetail = response._data
        result.value = taskDetail.results
        progress.value = taskDetail.done
        progressCount.value = `${taskDetail.done} / ${taskDetail.total}`
        if (taskDetail.total && taskDetail.total === taskDetail.done) {
          isUpdating.value = false
        }
        data.value = {
          resources: taskDetail.results.flatMap(result => result.repository_cached ?? []),
          total: taskDetail.total,
          pageSize: taskDetail.total,
          offset: 1,
        }
      },
    })
    await new Promise(resolve => setTimeout(resolve, config.loadingWaitTime))
  }
}
</script>

<template>
  <div>
    <UPageHeader
      :title="$t('cache-groups.title')"
      :description="$t('cache-groups.description')"
      :ui="{ root: 'py-2', description: 'mt-2' }"
    />
  </div>
  <div>
    <div v-if="isUpdating" class="flex flex-col items-center space-y-4 mb-4">
      <span class="text-lg font-medium text-gray-700">
        {{ $t('cache-groups.updating') }}
      </span>
      <span class="text-sm text-green-500">{{ progressCount }}</span>
      <UProgress v-model="progress" />
    </div>
    <div class="flex justify-end mb-4">
      <div class="flex space-x-2">
        <UModal :title="selectedModalTitle" :close="false" :ui="{ footer: 'justify-end' }">
          <UButton
            key="select"
            :label="$t('cache-groups.button.update-selected-repositories')"
            color="neutral"
            variant="soft"
            :disabled="isUpdating || selectedCount === 0"
            @click="onClickSelectRepositories"
          />
          <template #body>
            <div
              v-for="(repo, index) in selectedRows"
              :key="index" class="flex justify-center"
            >
              {{ repo.original.name }}
            </div>
          </template>
          <template #footer="{ close }">
            <UButton :label="$t('button.cancel')" color="neutral" variant="soft" @click="close" />
            <UButton
              :label="$t('button.update')"
              color="primary"
              variant="solid"
              @click="updateCaches(close, 'id-specified')"
            />
          </template>
        </UModal>
        <UModal :title="allModalTitle" :close="false" :ui="{ footer: 'justify-end' }">
          <UButton
            key="all"
            :label="$t('cache-groups.button.update-all-repositories')"
            color="neutral"
            variant="soft"
            :disabled="isUpdating"
            @click="onClickAllRepositories"
          />
          <template #footer="{ close }">
            <UButton :label="$t('button.cancel')" color="neutral" variant="soft" @click="close" />
            <UButton
              :label="$t('button.update')"
              color="primary"
              variant="solid"
              @click="updateCaches(close, 'all')"
            />
          </template>
        </UModal>
      </div>
    </div>
    <div class="flex justify-between mb-4">
      <div class="flex items-center space-x-2">
        <UInput
          v-model="searchTerm"
          :placeholder="$t('cache-groups.search-placeholder')"
          icon="i-lucide-search"
          :ui="{ base: 'w-s' }"
          :disabled="isUpdating"
          @keydown.enter="updateQuery({ q: searchTerm, p: 1 })"
        >
          <template #trailing>
            <UKbd value="enter" />
          </template>
        </UInput>
        <USelect
          v-model="filter"
          :placeholder="$t('cache-groups.filter-placeholder')"
          :items="filterItems"
          :ui="{ base: 'w-64' }"
          :disabled="isUpdating"
          multiple
          @change="updateQuery({ f: filter, p: 1 })"
        />
      </div>
      <div class="flex-1" />
      <div class="flex items-center space-x-2">
        <span class="text-sm text-gray-600">{{ $t('table.display-count-label') }}</span>
        <USelect
          v-model="pageSize"
          :items="pageOptions"
          :disabled="isUpdating"
          class="w-24"
          @change="updateQuery({ l: pageSize, p: 1 })"
        />
      </div>
    </div>
    <div>
      <ListRepositories
        :page-size="pageSize!"
        :columns="tableColumns"
        :data="data"
        :is-updateting="isUpdating"
        @page-change="updateQuery({ p: $event })"
      />
    </div>
  </div>
</template>
