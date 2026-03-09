<script setup lang="ts">
import type { ButtonProps, TableColumn } from '@nuxt/ui'

const page = ref(1)
const properties_ = defineProps({
  pageSize: {
    type: Number,
    required: true,
  },
  columns: {
    type: Array as () => Array<TableColumn<CacheGroupsSummary>>,
    required: true,
  },
  data: {
    type: Object as () => CacheGroupSearchResult | undefined,
    required: true,
  },
  isUpdateting: {
    type: Boolean,
    required: false,
    default: false,
  },
})
const emit = defineEmits<{
  (event: 'page-change', newPage: number): void
}>()
watch(page, (newPage) => {
  emit('page-change', newPage)
})

const displayInfo = computed(() => {
  if (properties_.isUpdateting) {
    const total = filteredData.value?.length ?? 0

    if (total === 0) {
      return $t('table.display-info-text-empty')
    }

    const start = (page.value - 1) * properties_.pageSize
    const end = Math.min(page.value * properties_.pageSize, total) - 1

    return $t('table.display-info-text', { start, end, total })
  }
  else {
    const start = properties_.data!.offset
    const end = properties_.data!.offset + properties_.pageSize - 1
    const total = properties_.data!.total
    return $t('table.display-info-text', { start, end, total })
  }
})

const filteredData = computed(() => {
  return properties_.data!.resources
})

const pagedData = computed(() => {
  if (properties_.isUpdateting) {
    const start = (page.value - 1) * properties_.pageSize
    return filteredData.value?.slice(start, start + properties_.pageSize) ?? []
  }
  else {
    return filteredData.value
  }
})

const isEmpty = computed(() => {
  return !properties_.data || properties_.data.resources.length === 0
})
// const isEmpty = ref(false)
const emptyActions = computed<ButtonProps[]>(() => [
  {
    icon: 'i-lucide-refresh-cw',
    label: $t('button.reload'),
    color: 'neutral',
    variant: 'subtle',
    onClick: () => {
      refreshNuxtData()
    },
  },
])
</script>

<template>
  <UEmpty
    v-if="isEmpty"
    :title="$t('repositories.list.no-repositories-title')"
    :description="$t('repositories.list.no-repositories-description')"
    :actions="emptyActions"
  />
  <div v-else>
    <UTable :columns="properties_.columns" :data="pagedData" />
    <div class="flex items-center mt-4">
      <div class="flex-1 text-gray-500 text-sm">
        {{ displayInfo }}
      </div>
      <div class="flex-2 flex justify-center">
        <UPagination
          v-model:page="page"
          :items-per-page="properties_.pageSize"
          :total="properties_.data!.total"
        />
      </div>
      <div class="flex-1" />
    </div>
  </div>
</template>
