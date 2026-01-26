<script setup lang="ts">
import { h, resolveComponent } from 'vue'

import type { SelectItem, StepperItem, TableColumn } from '@nuxt/ui'

const UBadge = resolveComponent('UBadge')
const UCheckbox = resolveComponent('UCheckbox')
const UIcon = resolveComponent('UIcon')

const route = useRoute()
const id = computed(() => route.params.id)

const selectedFile = ref<File | null>(null)
const deleteUnmatchedUsers = ref(false)
const selectedUnmatchedUserIds = ref<number[]>([])
const isProcessing = ref(false)
const currentStep = ref(id.value ? 2 : 0)

// ページネーション設定
const pageSize = ref(10)
const pagination = ref({
  pageIndex: 0,
  pageSize: pageSize.value,
})

const table = useTemplateRef('table')

const items: StepperItem[] = [
  {
    title: 'ファイル選択',
    description: 'CSVまたはTSVファイル',
    icon: 'i-lucide-file-up',
    slot: 'upload',
  },
  {
    title: 'データ検証',
    description: '変更内容の確認',
    icon: 'i-lucide-shield-check',
    slot: 'validation',
  },
  {
    title: '完了',
    description: 'インポート結果',
    icon: 'i-lucide-check-circle',
    slot: 'result',
  },
]

type ValidationStatus = 'ok' | 'warning' | 'error'
type OperationType = 'create' | 'update' | 'delete' | 'skip'

interface ValidationResult {
  row: number
  operation: OperationType
  status: ValidationStatus
  name: string
  eppn: string
  groups: string[]
  message?: string
}

interface UnmatchedUser {
  id: number
  name: string
  eppn: string
  groups: string[]
}

const validationResults = ref<ValidationResult[]>([])
const unmatchedUsers = ref<UnmatchedUser[]>([])

// 画面上部にスクロール
function scrollToTop() {
  window.scrollTo({
    top: 0,
    // behavior: 'smooth',
  })
}

// ファイル検証処理（画面表示用のサンプルデータのみ）
async function validateFile() {
  // if (!selectedFile.value) return

  isProcessing.value = true

  try {
    // 疑似的な処理時間
    // await new Promise(resolve => setTimeout(resolve, 1500))

    // 画面表示用のサンプルデータ
    validationResults.value = [
      // 正常な新規登録
      { row: 1, operation: 'create', status: 'ok', name: '山田太郎', eppn: 'yamada@example.ac.jp', groups: ['group-aaa'] },
      // 正常な更新
      { row: 2, operation: 'update', status: 'ok', name: '田中花子', eppn: 'tanaka@example.ac.jp', groups: ['group-bbb'], message: 'グループが変更されます' },
      // 警告付き更新
      { row: 3, operation: 'update', status: 'warning', name: '佐藤次郎', eppn: 'sato@example.ac.jp', groups: ['group-ccc'], message: '名前が変更されます' },
      // // エラー: eppn形式が不正
      // { row: 4, operation: 'create', status: 'error', name: '鈴木三郎', eppn: 'invalid-eppn', groups: ['group-ddd'], message: 'eppnの形式が不正です' },
      // // エラー: 必須項目（eppn）が不足
      // { row: 5, operation: 'create', status: 'error', name: '高橋四郎', eppn: '', groups: ['group-aaa'], message: '必須項目（eppn）が不足しています' },
      // // エラー: 必須項目（名前）が不足
      // { row: 6, operation: 'create', status: 'error', name: '', eppn: 'ito@example.ac.jp', groups: ['group-bbb'], message: '必須項目（名前）が不足しています' },
      // // エラー: 必須項目（グループ）が不足
      // { row: 7, operation: 'create', status: 'error', name: '渡辺五郎', eppn: 'watanabe@example.ac.jp', groups: [], message: '必須項目（グループ）が不足しています' },
      // スキップ: 更新前と同値
      { row: 4, operation: 'skip', status: 'ok', name: '中村六郎', eppn: 'nakamura@example.ac.jp', groups: ['group-aaa'], message: '更新前と同じ内容のためスキップします' },
      { row: 5, operation: 'skip', status: 'ok', name: '小林七郎', eppn: 'kobayashi@example.ac.jp', groups: ['group-ddd'], message: '更新前と同じ内容のためスキップします' },
      // { row: 5, operation: 'skip', status: 'ok', name: '小林七郎', eppn: 'kobayashi@example.ac.jp', groups: ['12345678901234567890123456789012345678901234567890'], message: '更新前と同じ内容のためスキップします' },
      // 以下、表示確認用のサンプルデータ
      ...Array.from({ length: 91 }, (_, index) => {
        const rand = Math.random()
        let operation: OperationType
        let status: ValidationStatus
        let message: string | undefined

        if (rand < 0.5) {
          operation = 'create'
          status = 'ok'
        }
        else if (rand < 0.75) {
          operation = 'update'
          status = 'ok'
          message = 'グループが変更されます'
        }
        else if (rand < 0.85) {
          operation = 'skip'
          status = 'ok'
          message = '更新前と同じ内容のためスキップします'
        }
        else if (rand < 0.95) {
          operation = 'update'
          status = 'warning'
          message = '名前が変更されます'
        }
        // else {
        //   operation = 'skip'
        //   status = 'error'
        //   message = '必須項目が不足しています'
        // }
        else {
          operation = 'create'
          status = 'ok'
        }

        return {
          row: index + 6,
          operation,
          status,
          name: status === 'error' && rand > 0.97 ? '' : `ユーザー${index + 6}`,
          eppn: status === 'error' && rand > 0.97 ? '' : `user${index + 6}@example.ac.jp`,
          groups: (() => {
            // ランダムに1〜3個のグループを選択
            const allGroups = ['group-aaa', 'group-bbb', 'group-ccc', 'group-ddd']
            const numberGroups = Math.floor(Math.random() * 3) + 1 // 1〜3個
            const shuffled = [...allGroups].toSorted(() => Math.random() - 0.5)
            return shuffled.slice(0, numberGroups)
          })(),
          message,
        }
      }),
    ]

    unmatchedUsers.value = [
      { id: 101, name: '伊藤八郎', eppn: 'ito@example.ac.jp', groups: ['group-aaa'] },
      { id: 102, name: '渡辺九郎', eppn: 'watanabe2@example.ac.jp', groups: ['group-bbb', 'group-ccc'] },
      { id: 103, name: '山本十郎', eppn: 'yamamoto@example.ac.jp', groups: ['group-ccc'] },
    ]

    pagination.value.pageIndex = 0
    currentStep.value = 1
    scrollToTop()
  }
  catch (error) {
    console.error('ファイルの検証に失敗しました:', error)
    useToast().add({
      title: 'エラー',
      description: 'ファイルの検証に失敗しました',
      color: 'error',
      icon: 'i-lucide-circle-x',
    })
  }
  finally {
    isProcessing.value = false
  }
}

// インポート実行（画面表示用）
async function executeImport() {
  isProcessing.value = true

  try {
    // await new Promise(resolve => setTimeout(resolve, 2000))

    // 実行結果データを生成（エラーとスキップは除外、削除を含む）
    const baseTime = new Date()

    importResults.value = [
      // バリデーション結果から正常なもののみを抽出して結果を生成
      ...validationResults.value
        .filter(r => r.status !== 'error' && r.operation !== 'skip')
        .map((r, index) => {
          const isFailed = Math.random() > 0.95
          return {
            operation: r.operation as ImportResultOperation,
            status: isFailed ? 'failed' : 'success',
            name: r.name,
            eppn: r.eppn,
            groups: r.groups,
            message: isFailed ? 'データベースエラーが発生しました' : undefined,
            timestamp: new Date(baseTime.getTime() + index * 100).toISOString(),
          }
        }),
      // 削除されたユーザー
      ...selectedUnmatchedUserIds.value.map((userId, index) => {
        const user = unmatchedUsers.value.find(u => u.id === userId)!
        return {
          operation: 'delete' as const,
          status: Math.random() > 0.98 ? 'failed' as const : 'success' as const,
          name: user.name,
          eppn: user.eppn,
          groups: user.groups,
          message: Math.random() > 0.98 ? '削除に失敗しました' : undefined,
          timestamp: new Date(baseTime.getTime() + (validationResults.value.length + index) * 100).toISOString(),
        }
      }),
    ]

    // useToast().add({
    //   title: '成功',
    //   description: 'インポートが完了しました',
    //   color: 'success',
    //   icon: 'i-lucide-circle-check',
    // })

    currentStep.value = 2

    // 画面上部にスクロール
    scrollToTop()
  }
  catch (error) {
    console.error('インポートに失敗しました:', error)
    useToast().add({
      title: 'エラー',
      description: 'インポートに失敗しました',
      color: 'error',
      icon: 'i-lucide-circle-x',
    })
  }
  finally {
    isProcessing.value = false
  }
}
function resetForm() {
  selectedFile.value = null
  validationResults.value = []
  unmatchedUsers.value = []
  deleteUnmatchedUsers.value = false
  selectedUnmatchedUserIds.value = []
  currentStep.value = 0
  pagination.value.pageIndex = 0
  resultPagination.value.pageIndex = 0 // 追加
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
    meta: {
      class: {
        td: 'w-20',
      },
    },
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

      return h(UBadge, {
        color: config.color,
        variant: 'subtle',
        class: 'gap-1',
      }, () => [
        h(UIcon, { name: config.icon, class: 'size-3' }),
        config.label,
      ])
    },
    meta: {
      class: {
        td: 'w-32',
      },
    },
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
      // (未入力)
    },
  },
  {
    accessorKey: 'groups',
    header: 'グループ',
    cell: ({ row }) => {
      const groups = row.getValue('groups') as string[]
      return groups && groups.length > 0
        ? h('div', { class: 'flex flex-col gap-1' },
            groups.map(group =>
              h('span', { class: 'font-mono text-sm' }, group),
            ),
          )
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

      return h(UBadge, {
        color: config.color,
        variant: 'subtle',
        class: 'gap-1',
      }, () => [
        h(UIcon, { name: config.icon, class: 'size-3' }),
        config.label,
      ])
    },
    meta: {
      class: {
        td: 'w-28',
      },
    },
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

const stepper = useTemplateRef('stepper')

const summary = computed(() => {
  const total = validationResults.value.length
  const byOperation = {
    create: validationResults.value.filter(r => r.operation === 'create' && r.status !== 'error').length,
    update: validationResults.value.filter(r => r.operation === 'update' && r.status !== 'error').length,
    delete: selectedUnmatchedUserIds.value.length,
    skip: validationResults.value.filter(r => r.operation === 'skip').length,
  }
  const byStatus = {
    ok: validationResults.value.filter(r => r.status === 'ok').length,
    warning: validationResults.value.filter(r => r.status === 'warning').length,
    error: validationResults.value.filter(r => r.status === 'error').length,
  }

  return { total, byOperation, byStatus }
})

const canProceed = computed(() => {
  if (currentStep.value === 0) {
    return selectedFile.value !== null
  }
  if (currentStep.value === 1) {
    return summary.value.byStatus.error === 0
    // return true
  }
  return false
})

async function handleNext() {
  if (currentStep.value === 0) {
    await validateFile()
  }
  else if (currentStep.value === 1) {
    await executeImport()
  }
}

function handlePrev() {
  if (currentStep.value > 0) {
    currentStep.value--
  }
}

function changePageSize(size: number) {
  pagination.value.pageSize = size
  pagination.value.pageIndex = 0
  pageSize.value = size
}

// 結果画面用のページサイズ変更
function changeResultPageSize(size: number) {
  resultPagination.value.pageSize = size
  resultPagination.value.pageIndex = 0
}

// ファイルダウンロード機能
function downloadFile() {
  if (!selectedFile.value) return

  // 実際の実装ではサーバーから取得したファイルをダウンロード
  // ここでは選択したファイルを再ダウンロード
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

// インポート結果用の型定義
type ImportResultStatus = 'success' | 'failed'
type ImportResultOperation = 'create' | 'update' | 'delete'

interface ImportResult {
  operation: ImportResultOperation
  status: ImportResultStatus
  name: string
  eppn: string
  groups: string[]
  message?: string
  timestamp: string // 処理日時
}

// インポート結果データ
const importResults = ref<ImportResult[]>([])

// 結果画面用のページネーション（検証画面とは別に管理）
const resultPagination = ref({
  pageIndex: 0,
  pageSize: 10,
})

const resultTable = useTemplateRef('resultTable')

// インポート結果用のカラム定義
const resultColumns: TableColumn<ImportResult>[] = [
  {
    accessorKey: 'operation',
    header: '操作',
    cell: ({ row }) => {
      const operation = row.getValue('operation') as ImportResultOperation
      const config = {
        create: { color: 'success' as const, label: '新規登録', icon: 'i-lucide-plus-circle' },
        update: { color: 'info' as const, label: '更新', icon: 'i-lucide-pencil' },
        delete: { color: 'error' as const, label: '削除', icon: 'i-lucide-trash-2' },
      }[operation]

      return h(UBadge, {
        color: config.color,
        variant: 'subtle',
        class: 'gap-1',
      }, () => [
        h(UIcon, { name: config.icon, class: 'size-3' }),
        config.label,
      ])
    },
    meta: {
      class: {
        td: 'w-32',
      },
    },
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
      return h('div', { class: 'flex flex-col gap-1' }, groups.map(group =>
        h('span', { class: 'font-mono text-sm' }, group),
      ))
    },
  },
  // {
  //   accessorKey: 'timestamp',
  //   header: '処理日時',
  //   cell: ({ row }) => {
  //     const timestamp = row.getValue('timestamp') as string
  //     return new Date(timestamp).toLocaleString('ja-JP', {
  //       month: '2-digit',
  //       day: '2-digit',
  //       hour: '2-digit',
  //       minute: '2-digit',
  //       second: '2-digit',
  //     })
  //   },
  //   meta: {
  //     class: {
  //       td: 'w-40',
  //     },
  //   },
  // },
  {
    accessorKey: 'status',
    header: 'ステータス',
    cell: ({ row }) => {
      const status = row.getValue('status') as ImportResultStatus
      const config = {
        success: { color: 'success' as const, label: '成功', icon: 'i-lucide-circle-check' },
        failed: { color: 'error' as const, label: '失敗', icon: 'i-lucide-circle-x' },
      }[status]

      return h(UBadge, {
        color: config.color,
        variant: 'subtle',
        class: 'gap-1',
      }, () => [
        h(UIcon, { name: config.icon, class: 'size-3' }),
        config.label,
      ])
    },
    meta: {
      class: {
        td: 'w-28',
      },
    },
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

// 結果画面用のサマリー
const resultSummary = computed(() => {
  const total = importResults.value.length
  const byOperation = {
    create: importResults.value.filter(r => r.operation === 'create').length,
    update: importResults.value.filter(r => r.operation === 'update').length,
    delete: importResults.value.filter(r => r.operation === 'delete').length,
    skip: summary.value.byOperation.skip, // 検証時のスキップ数を表示
  }
  const byStatus = {
    success: importResults.value.filter(r => r.status === 'success').length,
    failed: importResults.value.filter(r => r.status === 'failed').length,
  }

  return { total, byOperation, byStatus }
})

// リポジトリ選択用の状態
const selectedRepository = ref<string>()

// リポジトリのリスト（APIから取得する場合）
const repositories = ref<SelectItem[]>([
  { label: 'リポジトリA', value: 'repo-a' },
  { label: 'リポジトリB', value: 'repo-b' },
  { label: 'リポジトリC', value: 'repo-c' },
])

// インポート画面の進捗状況（0〜100）
const importProgress = ref(0)

// インポート進捗のシミュレーション
watch(currentStep, (newStep) => {
  if (newStep === 2) {
    importProgress.value = 0
    const interval = setInterval(() => {
      if (importProgress.value < 100) {
        importProgress.value += Math.floor(Math.random() * 10) + 5 // 5〜14ずつ増加
        if (importProgress.value > 100) {
          importProgress.value = 100
        }
      }
      else {
        clearInterval(interval)
      }
    }, 300)
  }
})

// urlにidがある場合初期データを読み込む
onMounted(async () => {
  if (id.value) {
    await loadData()
  }
})

async function loadData() {
  // ここでAPIからデータを取得する処理を実装
  // 例: const data = await fetchDataFromAPI(id.value)

  // サンプルデータの設定
  selectedFile.value = new File(
    ['name,eppn,groups\n山田太郎,yamada@example.ac.jp,group-sales\n田中花子,tanaka@example.ac.jp,group-dev'],
    'sample.csv',
    { type: 'text/csv' },
  )
  validateFile()
  executeImport()
}
</script>

<template>
  <UCard>
    <template #header>
      <h1 class="text-2xl font-bold">
        ユーザー一括操作
      </h1>
    </template>

    <UStepper
      ref="stepper"
      v-model="currentStep"
      :items="items"
      disabled
      orientation="horizontal"
      class="mb-8"
    >
      <!-- ステップ1: ファイル選択 -->
      <template #upload>
        <div class="space-y-4">
          <UAlert
            icon="i-lucide-info"
            color="warning"
            variant="subtle"
            title="一括操作について"
            :ui="{
              title: 'text-black',
              description: 'text-black',
            }"
          >
            <template #description>
              <ul class="list-disc list-inside space-y-1 text-sm">
                <li>ファイルに含まれるユーザーは<strong>新規登録または更新</strong>されます</li>
                <li>既存ユーザーはePPNで照合し、一致する場合は更新されます</li>
                <li>ファイルに含まれていないユーザーの<strong>削除</strong>を選択できます</li>
                <li>対応形式: TSV, CSV</li>
              </ul>
            </template>
          </UAlert>

          <!-- 操作対象リポジトリ選択 -->
          <UFormField
            label="操作対象リポジトリ"
            name="repository"
          >
            <USelectMenu
              v-model="selectedRepository"
              :items="repositories"
              placeholder="リポジトリを選択してください"
              value-key="value"
              class="w-full"
            >
              <template #item-leading="{ item }">
                <UIcon name="i-lucide-folder" class="size-5" />
              </template>
            </USelectMenu>
          </UFormField>

          <UFormField
            label="アップロードファイル"
            name="file"
          >
            <UFileUpload
              v-model="selectedFile"
              accept=".csv,.tsv,text/csv,text/tab-separated-values"
              label="ファイルを選択またはドラッグ&ドロップ"
              description="TSV, CSV"
              icon="i-lucide-file-up"
              layout="list"
              position="inside"
              color="primary"
            />
          </UFormField>

          <!-- <UCard variant="outline">
            <template #header>
              <p class="text-sm font-medium">
                ファイルフォーマット例
              </p>
            </template>
            <pre class="text-xs bg-elevated p-3 rounded overflow-x-auto">名前,eppn,グループ
山田太郎,yamada@example.ac.jp,group-sales
田中花子,tanaka@example.ac.jp,group-dev</pre>
            <template #footer>
              <p class="text-xs text-muted">
                ※ eppnは必須項目です。既存ユーザーとの照合に使用されます。
              </p>
            </template>
          </UCard> -->
        </div>
      </template>

      <!-- ステップ2: データ検証 -->
      <template #validation>
        <div class="space-y-4">
          <!-- エラーアラート -->
          <UAlert
            v-if="summary.byStatus.error > 0"
            color="error"
            icon="i-lucide-alert-circle"
            title="エラーが見つかりました"
            description="ファイルを修正して再度アップロードしてください。"
          />
          <!-- サマリーバー -->
          <div class="flex items-center justify-between p-4  rounded-lg border border-default">
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

          <!-- データプレビュー -->
          <UCard variant="outline">
            <template #header>
              <div class="flex items-center justify-between">
                <div>
                  <h3 class="text-lg font-semibold">
                    データプレビュー
                  </h3>
                  <!-- <p class="text-sm text-muted mt-0.5">
                    全{{ summary.total }}件のデータを確認してください
                  </p> -->
                </div>
                <div class="flex items-center gap-2">
                  <!-- <UInput
                    placeholder="検索..."
                    icon="i-lucide-search"
                    size="sm"
                    class="w-48"
                  /> -->
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
              ref="table"
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

          <!-- ファイルに含まれていないユーザー -->
          <UCard
            v-if="unmatchedUsers.length > 0"
            variant="outline"
          >
            <template #header>
              <div class="flex items-center justify-between">
                <div class="flex items-center gap-2">
                  <!-- <UIcon name="i-lucide-user-x" class="text-warning size-5" /> -->
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
                <!-- <UAvatar
                  :src="`https://i.pravatar.cc/120?img=${user.id}`"
                  size="sm"
                  :alt="`${user.name}のアバター`"
                /> -->
                <div class="flex-1">
                  <p class="font-medium">
                    {{ user.name }}
                  </p>
                  <p class="text-sm text-muted font-mono">
                    {{ user.eppn }}
                  </p>
                </div>
                <!-- <div class="text-right text-sm">
                  <p class="font-mono">
                    {{ user.groups.join(', ') }}
                  </p>
                </div> -->
                <div class="flex flex-col text-sm">
                  <div v-for="group in user.groups" :key="group">
                    <span>{{ group }}</span>
                  </div>
                </div>
              </div>
            </div>
          </UCard>
        </div>
      </template>

      <!-- ステップ3: 完了 -->
      <template #result>
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

          <!-- 成功メッセージ -->
          <!-- <UAlert
            icon="i-lucide-circle-check"
            color="success"
            title="一括処理が完了しました"
          >
            <template #description>
              <ul class="list-disc list-inside space-y-1 text-sm">
                <li><strong>{{ summary.byOperation.create }}件</strong>のユーザーを新規登録しました</li>
                <li><strong>{{ summary.byOperation.update }}件</strong>のユーザーを更新しました</li>
                <li v-if="summary.byOperation.delete > 0">
                  <strong>{{ summary.byOperation.delete }}件</strong>のユーザーを削除しました
                </li>
                <li v-if="summary.byOperation.skip > 0">
                  <strong>{{ summary.byOperation.skip }}件</strong>の行をスキップしました
                </li>
              </ul>
            </template>
          </UAlert> -->

          <!-- インポート情報 -->
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

            <div class="grid grid-cols-2 gap-x-8 gap-y-3 text-sm">
              <div class="flex justify-between">
                <span class="text-muted">ファイル名:</span>
                <span class="font-medium">{{ selectedFile?.name }}</span>
              </div>
              <div class="flex justify-between">
                <span class="text-muted">開始日時:</span>
                <span class="font-medium">{{ new Date().toLocaleString('ja-JP', {
                  year: 'numeric',
                  month: '2-digit',
                  day: '2-digit',
                  hour: '2-digit',
                  minute: '2-digit',
                  second: '2-digit',
                }) }}</span>
              </div>
              <div class="flex justify-between">
                <span class="text-muted">実行ユーザー:</span>
                <span class="font-medium">山田太郎</span>
              </div>
              <div class="flex justify-between">
                <span class="text-muted">終了日時:</span>
                <span class="font-medium">{{ new Date().toLocaleString('ja-JP', {
                  year: 'numeric',
                  month: '2-digit',
                  day: '2-digit',
                  hour: '2-digit',
                  minute: '2-digit',
                  second: '2-digit',
                }) }}</span>
              </div>
              <!-- <div class="flex justify-between">
                <span class="text-muted">総レコード数:</span>
                <span class="font-medium">{{ summary.total }}件</span>
              </div>
              <div class="flex justify-between">
                <span class="text-muted">ステータス:</span>
                <span class="font-medium">
                  正常終了
                </span>
              </div> -->
            </div>
          </UCard>

          <!-- <UCard>
            <template #header>
              <h3 class="text-lg font-semibold">
                インポート進捗
              </h3>
            </template>
            <div class="space-y-4 p-6">
              <p class="text-center text-2xl font-bold text-gray-900 dark:text-white">
                {{ Math.round(importProgress * summary.total / 100) }} / {{ summary.total }}
              </p>
              <UProgress v-model="importProgress" size="md" />
            </div>
          </UCard> -->

          <!-- インポート結果テーブル -->
          <UCard variant="outline">
            <template #header>
              <div class="flex items-center justify-between">
                <div>
                  <h3 class="text-lg font-semibold">
                    インポート結果
                  </h3>
                  <!-- <p class="text-sm text-muted mt-0.5">
                    全{{ resultSummary.total }}件の処理結果
                  </p> -->
                </div>
                <div class="flex items-center gap-2">
                  <!-- <UInput
                    placeholder="検索..."
                    icon="i-lucide-search"
                    size="sm"
                    class="w-48"
                  /> -->
                  <UDropdownMenu
                    :items="[
                      [
                        { label: 'すべて表示', type: 'checkbox', checked: true, onSelect: (e) => e.preventDefault() },
                        { label: '成功のみ', type: 'checkbox', checked: false, onSelect: (e) => e.preventDefault() },
                        { label: '失敗のみ', type: 'checkbox', checked: false, onSelect: (e) => e.preventDefault() },
                      ],
                      [
                        { label: '新規登録のみ', type: 'checkbox', checked: false, onSelect: (e) => e.preventDefault() },
                        { label: '更新のみ', type: 'checkbox', checked: false, onSelect: (e) => e.preventDefault() },
                        { label: '削除のみ', type: 'checkbox', checked: false, onSelect: (e) => e.preventDefault() },
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
                  <!-- <UButton
                    label="CSVでエクスポート"
                    icon="i-lucide-file-down"
                    size="sm"
                    color="neutral"
                    variant="outline"
                  /> -->
                  <UDropdownMenu
                    :items="[
                      [
                        { label: '10件', onSelect: () => changeResultPageSize(10) },
                        { label: '25件', onSelect: () => changeResultPageSize(25) },
                        { label: '50件', onSelect: () => changeResultPageSize(50) },
                        { label: '100件', onSelect: () => changeResultPageSize(100) },
                      ],
                    ]"
                  >
                    <UButton
                      :label="`${resultPagination.pageSize}件表示`"
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
              ref="resultTable"
              v-model:pagination="resultPagination"
              :data="importResults"
              :columns="resultColumns"
              sticky
            />

            <template #footer>
              <div class="flex items-center">
                <div class="flex flex-1 items-center gap-4">
                  <span class="text-sm text-muted">
                    {{ (resultPagination.pageIndex * resultPagination.pageSize) + 1 }}-{{ Math.min((resultPagination.pageIndex + 1) * resultPagination.pageSize, resultSummary.total) }} / {{ resultSummary.total }}件
                  </span>
                </div>

                <UPagination
                  :model-value="resultPagination.pageIndex + 1"
                  :total="resultSummary.total"
                  :items-per-page="resultPagination.pageSize"
                  class="flex-1"
                  @update:model-value="(page) => resultPagination.pageIndex = page - 1"
                />
                <div class="flex-1" />
              </div>
            </template>
          </UCard>
        </div>
      </template>
    </UStepper>

    <template #footer>
      <div class="flex justify-between">
        <UButton
          label="戻る"
          color="neutral"
          variant="outline"
          icon="i-lucide-arrow-left"
          :disabled="currentStep === 0 || isProcessing"
          @click="handlePrev"
        />
        <div class="flex gap-3">
          <!-- <UButton
            label="キャンセル"
            color="neutral"
            variant="outline"
            :disabled="isProcessing"
            @click="resetForm"
          /> -->
          <UButton
            v-if="currentStep < 2"
            :label="currentStep === 0 ? '次へ' : 'インポート実行'"
            :icon="isProcessing ? undefined : 'i-lucide-arrow-right'"
            :loading="isProcessing"
            trailing
            :disabled="!canProceed || isProcessing"
            @click="handleNext"
          >
            <template v-if="!canProceed && currentStep === 1 && summary.byStatus.error > 0" #trailing>
              <UTooltip text="エラーを修正してください">
                <UIcon name="i-lucide-alert-circle" class="size-4" />
              </UTooltip>
            </template>
          </UButton>
          <!-- <UButton
            v-else
            label="新しいインポート"
            icon="i-lucide-upload"
            @click="resetForm"
          /> -->
        </div>
      </div>
    </template>
  </UCard>
</template>
