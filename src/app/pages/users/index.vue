<script setup lang="ts">
const {
  query, updateQuery, criteria, creationButtons, emptyActions,
  selectedCount, selectedUsersActions, columns, columnNames, columnVisibility,
  makeAttributeFilters, dateFilter: { dateRange, formattedDateRange }, makePageInfo,
} = useUsersTable()

const { searchTerm, pageNumber, pageSize } = criteria

const table = useTemplateRef('table')
const { table: { pageSize: { users: pageOptions } } } = useAppConfig()

const { data: searchResult, status, refresh } = useFetch<UsersSearchResult>('/api/users', {
  method: 'GET',
  query,
  lazy: true,
  server: false,
})
const offset = computed(() => (searchResult.value?.offset ?? 1))
emptyActions.value[0]!.onClick = () => refresh()

const {
  data: filterOptions, status: filterOptionsStatus,
} = useFetch<FilterOption[]>('/api/users/filter-options', {
  method: 'GET',
  lazy: true,
  server: false,
})

const isFilterOpen = ref(false)
const filterSelects = makeAttributeFilters(filterOptions)
const pageInfo = makePageInfo(searchResult)
</script>

<template>
  <UPageHeader
    :title="$t('users.table.title')"
    :description="$t('users.description')"
    :ui="{ root: 'py-2 mb-6', description: 'mt-4' }"
  />

  <div class="flex justify-between items-center my-4">
    <div class="flex space-x-2">
      <UButton
        v-for="(button, index) in creationButtons"
        :key="index"
        :icon="button.icon" :label="button.label"
        :to="button.to" :color="button.color" :variant="button.variant"
        :ui="{ base: 'gap-1' }"
      />
    </div>

    <UDropdownMenu :items="selectedUsersActions">
      <UButton
        :label="$t('users.button.selected-users-actions')"
        color="warning" variant="subtle"
        :ui="{ base: 'gap-1' }"
        :disabled="selectedCount === 0"
      />
    </UDropdownMenu>
  </div>

  <div class="grid grid-cols-3 gap-4 my-4 h-8">
    <UInput
      v-model="searchTerm" :placeholder="$t('users.table.search-placeholder')"
      icon="i-lucide-search" :ui="{ trailing: 'pe-1.5' }"
      @keydown.enter="() => updateQuery({ q: searchTerm, p: 1 })"
    >
      <template #trailing>
        <UButton
          variant="ghost" color="neutral"
          :ui="{ base: 'font-normal cursor-pointer p-1' }"
          @click="() => updateQuery({ q: searchTerm, p: 1 })"
        >
          <UKbd value="enter" />
        </UButton>
      </template>
    </UInput>

    <div class="col-span-2 flex gap-4">
      <UButton
        :label="$t('table.filter-button-label')"
        color="neutral" variant="outline" icon="i-lucide-filter"
        :trailing-icon="isFilterOpen ? 'i-lucide-chevron-up' : 'i-lucide-chevron-down'"
        :loading="filterOptionsStatus === 'pending'"
        @click="isFilterOpen = !isFilterOpen"
      />
      <div class="flex flex-1 justify-end items-center space-x-4">
        <div class="flex items-center space-x-2">
          <label class="text-sm text-gray-600">{{ $t('table.page-size-label') }}</label>
          <USelect
            v-model="pageSize" :items="pageOptions"
            class="w-24"
            @update:model-value="() => updateQuery(
              { l: pageSize, p: Math.ceil(offset / pageSize!) },
            )"
          />
        </div>

        <UDropdownMenu
          :items="
            table?.tableApi
              ?.getAllColumns()
              .filter((column) => column.getCanHide())
              .map((column) => ({
                label: columnNames[column.id as keyof typeof columnNames],
                type: 'checkbox' as const,
                checked: column.getIsVisible(),
                onUpdateChecked(checked: boolean) {
                  table?.tableApi?.getColumn(column.id)?.toggleVisibility(!!checked)
                },
                onSelect(e: Event) {
                  e.preventDefault()
                },
              }))
          "
        >
          <UButton
            color="neutral" variant="outline"
            trailing-icon="i-lucide-chevron-down" :label="$t('table.display-columns-label')"
          />
        </UDropdownMenu>
      </div>
    </div>
  </div>

  <UCollapsible
    v-model:open="isFilterOpen"
    :ui="{ root: 'mb-4', content: 'grid grid-cols-3 gap-4' }"
  >
    <template #content>
      <USelectMenu
        v-for="(filter, index) in filterSelects"
        :key="index" :placeholder="filter.placeholder" :icon="filter.icon"
        :items="filter.items" :multiple="filter.multiple"
        :loading="filterOptionsStatus === 'pending'" :search-input="filter.searchInput"
        @update:model-value="filter.onUpdated"
      />

      <UPopover>
        <UInput
          icon="i-lucide-calendar"
          :placeholder="$t('users.table.column.last-modified')"
          :model-value="formattedDateRange"
          :ui="{ base: `text-left ${dateRange.start ? '' : 'text-dimmed'}` }" readonly
        >
          <template #trailing>
            <UButton
              v-if="dateRange.start" variant="ghost"
              color="neutral" icon="i-lucide-x"
              :ui="{ base: 'text-dimmed p-0' }"
              @click="() => {
                dateRange = { start: undefined, end: undefined }
                updateQuery({ s: undefined, e: undefined, p: 1 })
              }"
            />
            <div v-else />
          </template>
        </UInput>
        <template #content>
          <UCalendar
            v-model="dateRange" :number-of-months="2" class="p-2" range
            @update:valid-model-value="() => updateQuery(
              { s: dateRange.start?.toString(), e: dateRange.end?.toString(), p: 1 },
            )"
          />
        </template>
      </UPopover>
    </template>
  </UCollapsible>

  <UTable
    ref="table"
    v-model:column-visibility="columnVisibility"
    :loading="status === 'pending'"
    :data="searchResult?.resources" :columns="columns" :ui="{ root: 'mb-8' }"
  >
    <template #empty>
      <UEmpty
        :title="$t('users.table.no-users-title')"
        :description="$t('users.table.no-users-description')"
        :actions="emptyActions"
      />
    </template>
  </UTable>

  <div class="flex justify-center mt-4">
    <div class="flex-1 text-gray-500 text-sm">
      {{ pageInfo }}
    </div>
    <div class="flex-2 flex justify-center">
      <UPagination
        v-model:page="pageNumber"
        :items-per-page="pageSize"
        :total="searchResult?.total"
      />
    </div>
    <div class="flex-1" />
  </div>
</template>
