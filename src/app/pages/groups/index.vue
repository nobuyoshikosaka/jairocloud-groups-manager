<script setup lang="ts">
const toast = useToast()
const {
  query, updateQuery, criteria, creationButtons, emptyActions,
  toggleSelection, selectedCount, selectedGroupsActions,
  columns, columnNames, columnVisibility, makeAttributeFilters, makePageInfo,
} = useGroupsTable()

const { searchTerm, pageNumber, pageSize } = criteria

const table = useTemplateRef('table')
const { table: { pageSize: { groups: pageOptions } } } = useAppConfig()

const { handleFetchError } = useErrorHandling()
const { data: searchResult, status, refresh } = useFetch<GroupsSearchResult>('/api/groups', {
  method: 'GET',
  query,
  onResponseError({ response }) {
    switch (response.status) {
      case 400: {
        toast.add({
          title: $t('toast.error.failed-search.title'),
          description: $t('toast.error.invalid-search-query.description'),
          color: 'error',
        })
        break
      }
      default: {
        handleFetchError({ response })
        break
      }
    }
  },
  lazy: true,
  server: false,
})
const offset = computed(() => (searchResult.value?.offset ?? 1))
emptyActions.value[0]!.onClick = () => refresh()

const {
  data: filterOptions, status: filterOptionsStatus,
} = useFetch<FilterOption[]>('/api/groups/filter-options', {
  method: 'GET',
  onResponseError: async ({ response }) => { await handleFetchError({ response }) },
  lazy: true,
  server: false,
})

const isFilterOpen = ref(false)
const filterSelects = makeAttributeFilters(filterOptions)
const pageInfo = makePageInfo(searchResult)
</script>

<template>
  <UPageHeader
    :title="$t('groups.title')"
    :description="$t('groups.description')"
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

    <UDropdownMenu :items="selectedGroupsActions">
      <UButton
        :label="$t('groups.button.selected-groups-actions')"
        color="warning" variant="subtle"
        :ui="{ base: 'gap-1' }"
        :disabled="selectedCount === 0"
      />
    </UDropdownMenu>
  </div>

  <div class="grid grid-cols-3 gap-4 my-4 h-8">
    <UInput
      v-model="searchTerm" :placeholder="$t('groups.table.search-placeholder')"
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
        <div class="flex items-center">
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
        v-for="filter in filterSelects"
        :key="filter.key" :placeholder="filter.placeholder" :icon="filter.icon"
        :items="filter.items" :multiple="filter.multiple"
        :loading="filterOptionsStatus === 'pending'" :search-input="filter.searchInput"
        @update:model-value="filter.onUpdated"
      />
    </template>
  </UCollapsible>

  <UTable
    ref="table"
    v-model:column-visibility="columnVisibility"
    :loading="status === 'pending'"
    :data="searchResult?.resources" :columns="columns" :ui="{ root: 'mb-8' }"
    @select="toggleSelection"
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
        @update:page="(value) => updateQuery({ p: value })"
      />
    </div>
    <div class="flex-1" />
  </div>
</template>
