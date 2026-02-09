<script setup lang="ts" generic="T extends Record<string, any>">
import type { TableColumn } from '@nuxt/ui'

const { t: $t } = useI18n()

interface Properties<T> {
  data: T[]
  currentPage: number
  itemsPerPage: number
  totalItems: number
  emptyMessage?: string
  tableConfig?: {
    enableExpand?: boolean
    showStatus?: boolean
  }
  fileAvailabilityCheck?: (data: DownloadHistoryData) => boolean
}

const properties = computed(() => withDefaults(defineProps<Properties<T>>(), {
  emptyMessage: $t('history.empty-data'),
  tableConfig: () => ({ enableExpand: true, showStatus: false }),
}))

const emit = defineEmits<{
  'update:currentPage': [page: number]
  'update:itemsPerPage': [items: number]
  'action': [action: string, row: T]
  'sortChange': [payload?: string]
  'loadMoreChildren': [parentId: string, currentShown: number]
}>()

const columns = computed<TableColumn<T>[]>(() => {
  const base = [
    {
      id: 'timestamp',
      key: 'timestamp',
      label: $t('history.operation-date'),
      sortable: true,
    },
    {
      id: 'operator',
      key: 'operator',
      label: $t('history.operator'),
    },
    { id: 'users', key: 'users', label: $t('history.user-count') },
    { id: 'groups', key: 'groups', label: $t('history.group-count') },
  ]

  if (properties.value.tableConfig.enableExpand) {
    base.push({ id: 'redownload', key: 'redownload', label: $t('history.re-download') })
  }

  base.push({ id: 'actions', key: 'actions', label: '' })
  return base
})

const tableRows = computed(() => {
  const first = (properties.value.data as T[])[0]
  const looksLikeGroup = first && typeof first === 'object'
    && 'parent' in first && 'children' in first

  if (looksLikeGroup) {
    return (properties.value.data as T[]).map((item: T) => {
      const base = {
        ...item.parent,
        _children: item.children ?? [],
        _hasMore: !!item.hasMoreChildren,
        childrenCount: item.parent?.children_count ?? (item.children?.length ?? 0),
      }
      return {
        ...base,
        isDisabled: typeof properties.value.fileAvailabilityCheck === 'function'
          ? !properties.value.fileAvailabilityCheck(base)
          : false,
      }
    })
  }
  return (properties.value.data as T[]).map((r: T) => ({
    ...r,
    isDisabled: typeof properties.value.fileAvailabilityCheck === 'function'
      ? !properties.value.fileAvailabilityCheck(r)
      : false,
  }))
})

const pageStart = computed(() => properties.value.totalItems === 0
  ? 0
  : (properties.value.currentPage - 1) * properties.value.itemsPerPage + 1)

const pageEnd = computed(() => Math.min(
  properties.value.currentPage * properties.value.itemsPerPage,
  properties.value.totalItems,
))

const statusConfig = computed(() => ({
  S: { label: $t('history.succes'), color: 'success' as const },
  F: { label: $t('history.failed'), color: 'error' as const },
  P: { label: $t('history.progress'), color: 'warning' as const },
}))

const formatDate = (dateString: string) => {
  return new Date(dateString).toLocaleString('ja-JP', {
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit',
  })
}
</script>

<template>
  <UCard variant="outline" :ui="{ body: 'p-0' }">
    <template #header>
      <div class="flex items-center justify-between">
        <h2 class="text-xl font-semibold">
          {{ $t('history.table-title') }}
        </h2>
        <div class="flex items-center gap-2">
          <label class="text-sm text-gray-600">{{ $t('table.page-size-label') }}</label>
          <USelect
            v-model="pageSize" :items="pageOptions"
            class="w-24"
            @update:model-value="() => updateQuery(
              { l: pageSize, p: Math.ceil(offset / pageSize!) },
            )"
          />
        </div>
      </div>
    </template>

    <UTable
      :key="`ut-${properties.tableConfig.enableExpand?'d':'u'}-${properties.currentPage}
      -${properties.itemsPerPage}`"
      :rows="[...tableRows]"
      :columns="columns"
      row-key="id"
      :loading="false"
      @sort="(s) => emit('sortChange', s)"
    >
      <template #empty>
        <UEmpty
          icon="i-lucide-search-x"
          :title="properties.emptyMessage"
        />
      </template>

      <template #timestamp-data="{ row }">
        <div class="flex items-center gap-2">
          <UIcon
            v-if="row._matchedFields?.length"
            name="i-lucide-search-check"
            class="text-success"
          />
          <span :class="{ 'text-success font-bold': row._matchedFields?.includes('date') }">
            {{ formatDate(row.timestamp) }}
          </span>
        </div>
      </template>

      <template #operator-data="{ row }">
        <div class="flex items-center gap-2">
          <span>{{ row.operator?.user_name }}</span>
          <UBadge
            v-if="row.childrenCount > 0"
            :label="`+${row.childrenCount}`"
            size="xs"
            color="neutral"
            variant="subtle"
          />
        </div>
      </template>

      <template #users-data="{ row }">
        <UPopover mode="hover">
          <UButton
            color="neutral"
            variant="ghost"
            size="xs"
            :label="`${row.users?.length ?? 0}人`"
            trailing-icon="i-lucide-chevron-down"
          />
          <template #content>
            <div class="p-2 max-h-40 overflow-y-auto w-48">
              <div
                v-for="user in row.users"
                :key="user.id"
                class="text-sm py-1 border-b last:border-0 border-default"
              >
                {{ user.user_name }}
              </div>
            </div>
          </template>
        </UPopover>
      </template>

      <template #groups-data="{ row }">
        {{ row.groups?.length ?? 0 }}件
      </template>

      <template #redownload-data="{ row }">
        <UButton
          v-if="!row.isDisabled"
          :label="$t('history.re-download')"
          icon="i-lucide-download"
          size="sm"
          variant="outline"
          @click="$emit('action', 'redownload', row)"
        />
        <UBadge v-else :label="$t('history.expired')" color="neutral" variant="outline" />
      </template>

      <template #status-data="{ row }">
        <UBadge
          v-if="statusConfig[row.status]"
          :label="statusConfig[row.status].label"
          :color="statusConfig[row.status].color"
          variant="subtle"
        />
      </template>

      <template #actions-data="{ row }">
        <UDropdownMenu
          :items="[[{
            label: row.public ? $t('history.public') : $t('history.private'),
            icon: row.public ? 'i-lucide-eye':'i-lucide-eye-off',
            click: () => $emit('action', 'toggle-public', row),
          }]]"
        >
          <UButton icon="i-lucide-ellipsis-vertical" color="neutral" variant="ghost" />
        </UDropdownMenu>
      </template>

      <template #expand="{ row }">
        <div class="bg-elevated/5 px-12 py-2">
          <div
            v-for="child in row._children"
            :key="child.id"
            class="flex items-center py-2 text-sm border-b border-default/50"
          >
            <UIcon name="i-lucide-corner-down-right" class="mr-2 text-muted" />
            <span class="w-48">{{ formatDate(child.timestamp) }}</span>
            <span>{{ child.operator?.user_name }}</span>
          </div>
          <UButton
            v-if="row._hasMore"
            :label="$t('history.more')"
            variant="soft"
            size="xs"
            class="mt-2"
            @click="$emit('loadMoreChildren', row.id, row._children.length)"
          />
        </div>
      </template>
    </UTable>

    <template #footer>
      <div class="grid grid-cols-3 items-center">
        <p class="text-sm text-muted">
          {{ pageStart }}〜{{ pageEnd }} / {{ properties.totalItems }}件
        </p>
        <div class="flex justify-center">
          <UPagination
            :model-value="properties.currentPage"
            :total="properties.totalItems"
            :page-count="properties.itemsPerPage"
            @update:model-value="(p) => $emit('update:currentPage', p)"
          />
        </div>
        <div />
      </div>
    </template>
  </UCard>
</template>
