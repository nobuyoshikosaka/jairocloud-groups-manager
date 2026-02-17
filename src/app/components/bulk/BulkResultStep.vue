<script setup lang="ts">
const { t: $t } = useI18n()

const properties = defineProps<{
  historyId: string
  taskId: string
}>()

const {
  uploadResult,
  useBulkIndicators,
  fetchUploadResult,
} = useExecuteUpload()
const { makePageInfo } = useBulk()

const toast = useToast()
const url = `/api/bulk/result/${properties.historyId}`

const { data: status, execute: executeStatus }
  = await useFetch<BulkProcessingStatus>(`/api/bulk/execute/status/${properties.taskId}`)
const { polling: { interval, maxAttempts } } = useAppConfig()
const pollExecuteStatus = async () => {
  for (let index = 0; index < maxAttempts; index++) {
    await executeStatus()
    const st = (status.value?.status)
    if (st === 'SUCCESS') return
    if (st === 'FAILURE') {
      toast.add({
        title: $t('bulk.status.error'),
        description: $t('bulk.execute.failed'),
        color: 'error',
        icon: 'i-lucide-circle-x',
      })
      return
    }
    const { uploadResult: result } = await fetchUploadResult(url)
    uploadResult.value = result.value
    await new Promise(r => setTimeout(r, interval))
  }
  toast.add({
    title: $t('bulk.status.error'),
    description: $t('bulk.execute.timeout'),
    color: 'error',
    icon: 'i-lucide-circle-x',
  })
}
onMounted(async () => {
  await pollExecuteStatus()
})

const indicators = useBulkIndicators
const fileInfo = computed(() => uploadResult.value!.fileInfo)
const pageInfo = makePageInfo(uploadResult)
</script>

<template>
  <div class="space-y-4">
    <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
      <NumberIndicator
        v-for="indicator in indicators"
        :key="indicator.key"
        :title="indicator.title"
        :icon="indicator.icon"
        :number="indicator.number"
        :color="indicator.color"
      />
    </div>

    <div class="flex items-center justify-between">
      <h3 class="text-lg font-semibold">
        {{ $t('bulk.upload-file-info') }}
      </h3>
    </div>

    <div class="grid grid-cols-2 gap-x-8 gap-y-3 text-sm">
      <div class="flex justify-between">
        <span class="text-muted">{{ $t('bulk.upload-file') }}:</span>
        <span class="font-medium">{{ fileInfo.fileName || '-' }}</span>
      </div>
      <div class="flex justify-between">
        <span class="text-muted">{{ $t('bulk.start-at') }}:</span>
        <span class="font-medium">
          {{ fileInfo.startedAt ? new Date(fileInfo.startedAt).toLocaleString('ja-JP') : '-' }}
        </span>
      </div>
      <div class="flex justify-between">
        <span class="text-muted">{{ $t('bulk.operator') }}:</span>
        <span class="font-medium">{{ fileInfo.executedBy || '-' }}</span>
      </div>
      <div class="flex justify-between">
        <span class="text-muted">{{ $t('bulk.completed-at') }}:</span>
        <span class="font-medium">
          {{ fileInfo.completedAt ? new Date(fileInfo.completedAt).toLocaleString('ja-JP')
            : '-' }}
        </span>
      </div>
    </div>

    <BulkUserTable
      :data="uploadResult!.results"
      :total-count="uploadResult!.total"
      :page-info="pageInfo"
      :offset="uploadResult!.offset"
      :title="$t('bulk.import-results')"
    />
  </div>
</template>
