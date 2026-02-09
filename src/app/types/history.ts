/**
 * Types related to history
 */
interface DownloadHistoryData {
  id: string
  timestamp: string
  operator: UserSummary
  public: boolean
  parent_id: string | undefined
  file_path: string
  file_id: string
  repositories: RepositorySummary[]
  groups: GroupSummary[]
  users: UserSummary[]
  children_count: number
}

interface UploadHistoryData {
  id: string
  timestamp: string
  end_timestamp?: string | undefined
  public: boolean
  operator: UserSummary
  status: 'S' | 'F' | 'P'
  file_path: string
  file_id: string
  repositories: RepositorySummary[]
  groups: GroupSummary[]
  users: UserSummary[]
}

interface PaginationInfo {
  page: number
  per_page: number
  total: number
}

interface DownloadApiModel {
  download_history_data: DownloadHistoryData[]
  pagination?: PaginationInfo
  summary?: {
    total: number
    first: number
    redownload: number
  }
  sum_download?: number
  first_download?: number
  re_download?: number
}

interface UploadApiModel {
  upload_history_data: UploadHistoryData[]
  pagination?: PaginationInfo
  summary?: {
    total: number
    success: number
    failed: number
    progress: number
  }
  sum_upload?: number
  success_upload?: number
  failed_upload?: number
  progress_upload?: number
}

interface HistoryQuery {
  tab?: string
  p?: string
  l?: string
  d?: string
  s?: string
  e?: string
  o?: string[]
  r?: string[]
  g?: string[]
  u?: string[]
  i?: string[]
}

interface DownloadGroupItem {
  parent: DownloadHistoryData
  children: DownloadHistoryData[]
  hasMoreChildren: boolean
  childrenLimit: number
}

interface TableConfig {
  enableExpand?: boolean
  showStatus?: boolean
}

interface FilterOptionsResponse {
  operators?: Array<{ id: string, user_name?: string | null }>
  target_repositories?: Array<{ id: string, display_name?: string | null }>
  target_groups?: Array<{ id: string, display_name?: string | null }>
  target_users?: Array<{ id: string, user_name?: string | null }>
}

interface SelectOption {
  label: string
  value: string
}

interface StatusConfig {
  label: string
  color: 'success' | 'error' | 'warning' | 'info'
}

interface HistoryStats {
  sum?: number
  firstDownload?: number
  reDownload?: number
  success?: number
  error?: number
}

interface PublicStatusUpdateRequest {
  public: boolean
}

type ActionRow = DownloadGroupItem | UploadHistoryData

export type { DownloadHistoryData, UploadHistoryData, DownloadApiModel, UploadApiModel,
  HistoryQuery, TableConfig, FilterOptionsResponse, SelectOption, StatusConfig, HistoryStats,
  PublicStatusUpdateRequest, ActionRow, DownloadGroupItem }
