<script setup lang="ts">
import { h, resolveComponent } from 'vue'

import type { TableColumn } from '@nuxt/ui'
import type { UploadResult, UploadResultOperation, UploadResultStatus } from '~/types/userUpload'

const UBadge = resolveComponent('UBadge')
const UIcon = resolveComponent('UIcon')

const router = useRouter()

const {
  selectedFile,
  uploadResults,
  summary,
  resetUpload,
} = useUserUpload()

// インポート結果がない場合は戻る
onMounted(() => {
  if (uploadResults.value.length === 0) {
    router.push('/bulk')
  }
})

const resultPagination = ref({
  pageIndex: 0,
  pageSize: 10,
})

function changeResultPageSize(size: number) {
  resultPagination.value.pageSize = size
  resultPagination.value.pageIndex = 0
}

function downloadFile() {
  if (!selectedFile.value) return

  const url = URL.createObjectURL(selectedFile.value)
  const a = document.createElement('a')
  a.href = url
  a.download = selectedFile.value.name
  document.body.append(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)

  useToast().add({
    title: 'ダウンロード開始',
    description: 'ファイルのダウンロードを開始しました',
    color: 'success',
    icon: 'i-lucide-download',
  })
}

async function handleNewUpload() {
  resetUpload()
  await router.push('/bulk')
}

const resultColumns: TableColumn<UploadResult>[] = [
  {
    accessorKey: 'operation',
    header: '操作',
    cell: ({ row }) => {
      const operation = row.getValue('operation') as UploadResultOperation
      const config = {
        create: { color: 'success' as const, label: '新規登録', icon: 'i-lucide-plus-circle' },
        update: { color: 'info' as const, label: '更新', icon: 'i-lucide-pencil' },
        delete: { color: 'error' as const, label: '削除', icon: 'i-lucide-trash-2' },
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
  },
  {
    accessorKey: 'eppn',
    header: 'eppn',
    cell: ({ row }) => h('span', { class: 'font-mono text-sm' }, row.getValue('eppn') as string),
  },
  {
    accessorKey: 'groups',
    header: 'グループ',
    cell: ({ row }) => {
      const groups = row.getValue('groups') as string[]
      return h('div', { class: 'flex flex-col gap-1' },
        groups.map(group => h('span', { class: 'font-mono text-sm' }, group)))
    },
  },
  {
    accessorKey: 'status',
    header: 'ステータス',
    cell: ({ row }) => {
      const status = row.getValue('status') as UploadResultStatus
      const config = {
        success: { color: 'success' as const, label: '成功', icon: 'i-lucide-circle-check' },
        failed: { color: 'error' as const, label: '失敗', icon: 'i-lucide-circle-x' },
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
        ユーザー一括操作 - 完了
      </h1>
    </template>

    <div class="space-y-4">
      <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
        <UCard variant="outline">
          <div class="flex items-center gap-3">
            <div class="p-3 bg-success/10 rounded-lg">
              <UIcon name="i-lucide-plus-circle" class="size-6 text-success" />
            </div>
            <div>
              <p class="text-2xl font-bold">
                {{ summary.byOperation.create }}
              </p>
              <p class="text-sm text-muted">
                新規登録
              </p>
            </div>
          </div>
        </UCard>

        <UCard variant="outline">
          <div class="flex items-center gap-3">
            <div class="p-3 bg-info/10 rounded-lg">
              <UIcon name="i-lucide-pencil" class="size-6 text-info" />
            </div>
            <div>
              <p class="text-2xl font-bold">
                {{ summary.byOperation.update }}
              </p>
              <p class="text-sm text-muted">
                更新
              </p>
            </div>
          </div>
        </UCard>

        <UCard variant="outline">
          <div class="flex items-center gap-3">
            <div class="p-3 bg-error/10 rounded-lg">
              <UIcon name="i-lucide-trash-2" class="size-6 text-error" />
            </div>
            <div>
              <p class="text-2xl font-bold">
                {{ summary.byOperation.delete }}
              </p>
              <p class="text-sm text-muted">
                削除
              </p>
            </div>
          </div>
        </UCard>

        <UCard variant="outline">
          <div class="flex items-center gap-3">
            <div class="p-3 bg-warning/10 rounded-lg">
              <UIcon name="i-lucide-minus-circle" class="size-6 text-warning" />
            </div>
            <div>
              <p class="text-2xl font-bold">
                {{ summary.byOperation.skip }}
              </p>
              <p class="text-sm text-muted">
                スキップ
              </p>
            </div>
          </div>
        </UCard>
      </div>

      <UCard variant="outline">
        <template #header>
          <div class="flex items-center justify-between">
            <h3 class="text-lg font-semibold">
              インポート情報
            </h3>
            <UButton
              label="ファイルをダウンロード"
              icon="i-lucide-download"
              size="sm"
              color="neutral"
              variant="outline"
              @click="downloadFile"
            />
          </div>
        </template>
      </ucard>
    </div>
  </ucard>
</template>
