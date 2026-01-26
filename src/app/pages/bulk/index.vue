<script setup lang="ts">
const {
  selectedFile,
  selectedRepository,
  validateFile,
  isProcessing,
} = useUserUpload()

const router = useRouter()

const canProceed = computed(() => selectedFile.value !== null
  && selectedRepository.value !== undefined)

async function handleNext() {
  try {
    await validateFile()
    await router.push('/bulk/validation')
    window.scrollTo({ top: 0 })
  }
  catch {
    useToast().add({
      title: 'エラー',
      description: 'ファイルの検証に失敗しました',
      color: 'error',
      icon: 'i-lucide-circle-x',
    })
  }
}
const repositories = ref([])
const isLoadingRepositories = ref(false)

async function fetchRepositories() {
  isLoadingRepositories.value = true
  try {
    const data = await $fetch('/api/repositories')
    repositories.value = data.map(repo => ({
      value: repo.id,
      label: repo.name,
      ...repo,
    }))
  }
  catch {
    repositories.value = []
  }
  finally {
    isLoadingRepositories.value = false
  }
}

fetchRepositories()
</script>

<template>
  <UCard>
    <template #header>
      <h1 class="text-2xl font-bold">
        ユーザー一括操作 - ファイル選択
      </h1>
    </template>

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
            <li>既存ユーザーはidで照合し、一致する場合は更新されます</li>
            <li>ファイルに含まれていないユーザーの<strong>削除</strong>を選択できます</li>
            <li>対応形式: TSV, CSV</li>
          </ul>
        </template>
      </UAlert>

      <UFormField
        label="操作対象リポジトリ"
        name="repository"
      >
        <USelectMenu
          v-model="selectedRepository"
          :items="repositories"
          :loading="!repositories || repositories.length === 0"
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
    </div>

    <template #footer>
      <div class="flex justify-end">
        <UButton
          label="次へ"
          icon="i-lucide-arrow-right"
          trailing
          :loading="isProcessing"
          :disabled="!canProceed || isProcessing"
          @click="handleNext"
        />
      </div>
    </template>
  </UCard>
</template>
