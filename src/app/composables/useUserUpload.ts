export function useUserUpload() {
  const selectedFile = ref<File | null>(null)
  const selectedRepository = ref()
  const isProcessing = ref(false)

  // Fetch repositories from API
  const { data: repositories, status, error } = useFetch('/api/repositories', {
    default: () => [],
    // Transform the response if needed
    transform: (data) => {
      // Assuming API returns array of repositories
      // Transform to match USelectMenu format with value and label
      return data.map(repo => ({
        value: repo.id, // or whatever unique identifier
        label: repo.name, // display name
        ...repo, // include other properties if needed
      }))
    },
  })

  async function validateFile() {
    isProcessing.value = true
    try {
      // Your validation logic
    }
    finally {
      isProcessing.value = false
    }
  }

  return {
    selectedFile,
    selectedRepository,
    repositories,
    validateFile,
    isProcessing,
  }
}
