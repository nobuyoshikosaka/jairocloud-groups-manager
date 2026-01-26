<script setup lang="ts">
import { h, resolveComponent } from 'vue'

import type { TableColumn } from '@nuxt/ui'
import type { OperationType, ValidationResult, ValidationStatus } from '~/types/userUpload'

const UBadge = resolveComponent('UBadge')
const UCheckbox = resolveComponent('UCheckbox')
const UIcon = resolveComponent('UIcon')

const router = useRouter()

const {
  selectedFile,
  validationResults,
  unmatchedUsers,
  selectedUnmatchedUserIds,
  summary,
  executeUpload,
  isProcessing,
} = useUserUpload()

// ファイルが選択されていない場合は戻る
onMounted(() => {
  if (!selectedFile.value) {
    router.push('/bulk')
  }
})

const pagination = ref({
  pageIndex: 0,
  pageSize: 10,
})

const canProceed = computed(() => summary.value.byStatus.error === 0)

async function handleNext() {
  try {
    await executeUpload()
    await router.push('/bulk/result')
    window.scrollTo({ top: 0 })
  }
  catch {
    useToast().add({
      title: 'エラー',
      description: 'インポートに失敗しました',
      color: 'error',
      icon: 'i-lucide-circle-x',
    })
  }
}

function handlePrev() {
  router.push('/bulk')
}

function changePageSize(size: number) {
  pagination.value.pageSize = size
  pagination.value.pageIndex = 0
}

function selectAllUnmatchedUsers() {
  selectedUnmatchedUserIds.value = unmatchedUsers.value.map(u => u.id)
}

function deselectAllUnmatchedUsers() {
  selectedUnmatchedUserIds.value = []
}

function toggleUnmatchedUser(userId: number) {
  const index = selectedUnmatchedUserIds.value.indexOf(userId)
  if (index === -1) {
    selectedUnmatchedUserIds.value.push(userId)
  }
  else {
    selectedUnmatchedUserIds.value.splice(index, 1)
  }
}

const columns: TableColumn<ValidationResult>[] = [
  {
    accessorKey: 'row',
    header: '行',
    cell: ({ row }) => `${row.getValue('row')}行目`,
    meta: { class: { td: 'w-20' } },
  },
  {
    accessorKey: 'operation',
    header: '操作',
    cell: ({ row }) => {
      const operation = row.getValue('operation') as OperationType
      const config = {
        create: { color: 'success' as const, label: '新規登録', icon: 'i-lucide-plus-circle' },
        update: { color: 'info' as const, label: '更新', icon: 'i-lucide-pencil' },
        delete: { color: 'error' as const, label: '削除', icon: 'i-lucide-trash-2' },
        skip: { color: 'neutral' as const, label: 'スキップ', icon: 'i-lucide-minus-circle' },
      }[operation]

      return h(UBadge, { color: config.color, variant: 'subtle', class: 'gap-1' }, () => [
        h(UIcon, { name: config.icon, class: 'size-3' }),
        config.label,
      ])
    },
    meta: { class: { td: 'w-32' } },
  },
  {
    accessorKey: 'name',
    header: '名前',
    cell: ({ row }) => {
      const name = row.getValue('name') as string
      return name || h('span', { class: 'text-muted italic' }, '')
    },
  },
  {
    accessorKey: 'eppn',
    header: 'eppn',
    cell: ({ row }) => {
      const eppn = row.getValue('eppn') as string
      return eppn
        ? h('span', { class: 'font-mono text-sm' }, eppn)
        : h('span', { class: 'text-muted italic' }, '')
    },
  },
  {
    accessorKey: 'groups',
    header: 'グループ',
    cell: ({ row }) => {
      const groups = row.getValue('groups') as string[]
      return groups && groups.length > 0
        ? h('div', { class: 'flex flex-col gap-1' }, groups.map(group => h('span', { class: 'font-mono text-sm' }, group)))
        : h('span', { class: 'text-muted italic' }, '')
    },
  },
  {
    accessorKey: 'status',
    header: 'ステータス',
    cell: ({ row }) => {
      const status = row.getValue('status') as ValidationStatus
      const config = {
        ok: { color: 'success' as const, label: '正常', icon: 'i-lucide-circle-check' },
        warning: { color: 'warning' as const, label: '警告', icon: 'i-lucide-alert-triangle' },
        error: { color: 'error' as const, label: 'エラー', icon: 'i-lucide-circle-x' },
      }[status]

      return h(UBadge, { color: config.color, variant: 'subtle', class: 'gap-1' }, () => [
        h(UIcon, { name: config.icon, class: 'size-3' }),
        config.label,
      ])
    },
    meta: { class: { td: 'w-28' } },
  },
  {
    accessorKey: 'message',
    header: 'メッセージ',
    cell: ({ row }) => {
      const message = row.getValue('message')
      return message ? h('span', { class: 'text-sm text-muted' }, message as string) : '-'
    },
  },
]
</script>

<template>
  <UCard>
    <template #header>
      <h1 class="text-2xl font-bold">
        ユーザー一括操作 - データ検証
      </h1>
    </template>

    <div class="space-y-4">
      <UAlert
        v-if="summary.byStatus.error > 0"
        color="error"
        icon="i-lucide-alert-circle"
        title="エラーが見つかりました"
        description="ファイルを修正して再度アップロードしてください。"
      />

      <div class="flex items-center justify-between p-4 rounded-lg border border-default">
        <div class="flex items-center gap-6">
          <div class="flex items-center gap-2">
            <UIcon name="i-lucide-plus-circle" class="size-4 text-success" />
            <span class="text-sm">新規 <strong class="text-base">{{ summary.byOperation.create }}</strong></span>
          </div>
          <div class="flex items-center gap-2">
            <UIcon name="i-lucide-pencil" class="size-4 text-info" />
            <span class="text-sm">更新 <strong class="text-base">{{ summary.byOperation.update }}</strong></span>
          </div>
          <div class="flex items-center gap-2">
            <UIcon name="i-lucide-trash-2" class="size-4 text-error" />
            <span class="text-sm">削除 <strong class="text-base">{{ summary.byOperation.delete }}</strong></span>
          </div>
          <div class="flex items-center gap-2">
            <UIcon name="i-lucide-minus-circle" class="size-4 text-muted" />
            <span class="text-sm">スキップ <strong class="text-base">{{ summary.byOperation.skip }}</strong></span>
          </div>
        </div>

        <div class="flex items-center gap-2">
          <UBadge color="success" variant="subtle" size="md">
            正常 {{ summary.byStatus.ok }}
          </UBadge>
          <UBadge v-if="summary.byStatus.warning > 0" color="warning" variant="subtle" size="md">
            警告 {{ summary.byStatus.warning }}
          </UBadge>
          <UBadge v-if="summary.byStatus.error > 0" color="error" variant="subtle" size="md">
            エラー {{ summary.byStatus.error }}
          </UBadge>
        </div>
      </div>

      <UCard variant="outline">
        <template #header>
          <div class="flex items-center justify-between">
            <div>
              <h3 class="text-lg font-semibold">
                データプレビュー
              </h3>
            </div>
            <div class="flex items-center gap-2">
              <UDropdownMenu
                :items="[
                  [
                    { label: 'すべて表示', type: 'checkbox', checked: true, onSelect: (e) => e.preventDefault() },
                    { label: 'エラーのみ', type: 'checkbox', checked: false, onSelect: (e) => e.preventDefault() },
                    { label: '警告のみ', type: 'checkbox', checked: false, onSelect: (e) => e.preventDefault() },
                  ],
                  [
                    { label: '新規登録のみ', type: 'checkbox', checked: false, onSelect: (e) => e.preventDefault() },
                    { label: '更新のみ', type: 'checkbox', checked: false, onSelect: (e) => e.preventDefault() },
                  ],
                ]"
              >
                <UButton
                  label="フィルター"
                  icon="i-lucide-filter"
                  size="sm"
                  color="neutral"
                  variant="outline"
                  trailing-icon="i-lucide-chevron-down"
                />
              </UDropdownMenu>
              <UDropdownMenu
                :items="[
                  [
                    { label: '10件', onSelect: () => changePageSize(10) },
                    { label: '25件', onSelect: () => changePageSize(25) },
                    { label: '50件', onSelect: () => changePageSize(50) },
                    { label: '100件', onSelect: () => changePageSize(100) },
                  ],
                ]"
              >
                <UButton
                  :label="`${pagination.pageSize}件表示`"
                  size="sm"
                  color="neutral"
                  variant="outline"
                  trailing-icon="i-lucide-chevron-down"
                />
              </UDropdownMenu>
            </div>
          </div>
        </template>

        <UTable
          v-model:pagination="pagination"
          :data="validationResults"
          :columns="columns"
          sticky
        />

        <template #footer>
          <div class="flex items-center">
            <div class="flex items-center gap-4 flex-1">
              <span class="text-sm text-muted">
                {{ (pagination.pageIndex * pagination.pageSize) + 1 }}-{{ Math.min((pagination.pageIndex + 1) * pagination.pageSize, summary.total) }} / {{ summary.total }}件
              </span>
            </div>

            <UPagination
              :model-value="pagination.pageIndex + 1"
              :total="summary.total"
              :items-per-page="pagination.pageSize"
              size="xs"
              class="flex-1"
              @update:model-value="(page) => pagination.pageIndex = page - 1"
            />
            <div class="flex-1" />
          </div>
        </template>
      </UCard>

      <UCard v-if="unmatchedUsers.length > 0" variant="outline">
        <template #header>
          <div class="flex items-center justify-between">
            <div class="flex items-center gap-2">
              <h3 class="font-semibold">
                ファイルに含まれていないユーザー ({{ unmatchedUsers.length }}件)
              </h3>
            </div>
            <div class="flex items-center gap-2">
              <UButton
                label="すべて選択"
                size="xs"
                color="neutral"
                variant="outline"
                @click="selectAllUnmatchedUsers"
              />
              <UButton
                label="すべて解除"
                size="xs"
                color="neutral"
                variant="outline"
                @click="deselectAllUnmatchedUsers"
              />
            </div>
          </div>
          <p class="text-sm text-muted">
            削除するユーザーを選択してください。
          </p>
        </template>

        <UAlert
          v-if="selectedUnmatchedUserIds.length > 0"
          color="error"
          icon="i-lucide-alert-triangle"
          title="削除の確認"
          :description="`選択した${selectedUnmatchedUserIds.length}件のユーザーは削除されます。この操作は元に戻せません。`"
          class="mb-4"
          variant="solid"
        />

        <div class="space-y-2">
          <div
            v-for="user in unmatchedUsers"
            :key="user.id"
            class="flex items-center gap-3 p-3 rounded-lg border cursor-pointer hover:bg-elevated/50 transition-colors"
            :class="selectedUnmatchedUserIds.includes(user.id) ? 'border-error bg-error/5' : 'border-default'"
            @click="toggleUnmatchedUser(user.id)"
          >
            <UCheckbox
              :model-value="selectedUnmatchedUserIds.includes(user.id)"
              @click.stop
              @update:model-value="toggleUnmatchedUser(user.id)"
            />
            <div class="flex-1">
              <p class="font-medium">
                {{ user.name }}
              </p>
              <p class="text-sm text-muted font-mono">
                {{ user.eppn }}
              </p>
            </div>
            <div class="flex flex-col text-sm">
              <div v-for="group in user.groups" :key="group">
                <span>{{ group }}</span>
              </div>
            </div>
          </div>
        </div>
      </UCard>
    </div>

    <template #footer>
      <div class="flex justify-between">
        <UButton
          label="戻る"
          color="neutral"
          variant="outline"
          icon="i-lucide-arrow-left"
          :disabled="isProcessing"
          @click="handlePrev"
        />
        <UButton
          label="インポート実行"
          icon="i-lucide-arrow-right"
          trailing
          :loading="isProcessing"
          :disabled="!canProceed || isProcessing"
          @click="handleNext"
        >
          <template v-if="!canProceed && summary.byStatus.error > 0" #trailing>
            <UTooltip text="エラーを修正してください">
              <UIcon name="i-lucide-alert-circle" class="size-4" />
            </UTooltip>
          </template>
        </UButton>
      </div>
    </template>
  </UCard>
</template>
