/**
 * Types related to cache groups
 */

/** Cache group summary information */
interface CacheGroupsSummary {
  id: string
  name: string
  url: string
  updated: string
}

/** Search result for cache groups */
interface CacheGroupSearchResult {
  total: number
  pageSize: number
  offset: number
  resources: CacheGroupsSummary[]
}

/** Cache groups update result */
interface CacheGroupsUpdateResult {
  type: string
  fqdn: string
  status: string
  code?: string
  repository_cached?: CacheGroupsSummary[]
}

/** Detail information of a cache groups update task */
interface TaskDetail {
  results: CacheGroupsUpdateResult[]
  current: string
  done: number
  total: number
}

export type { CacheGroupsSummary, CacheGroupSearchResult, CacheGroupsUpdateResult, TaskDetail }
