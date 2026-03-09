/**
 * Types related to repositories
 */

/** Repository summary information */
interface RepositorySummary {
  id: string
  serviceName: string
  serviceUrl: string
  spConnectorId?: string
  entityIds?: [string, ...string[]]
}

/** Repository detailed information */
interface RepositoryDetail extends RepositorySummary {
  active?: boolean
  created?: string
  usersCount?: number
  groupsCount?: number
}

type RepositoryForm = Required<Omit<RepositoryDetail, 'usersCount' | 'groupsCount'>>

type RepositoryUpdatePayload = Omit<RepositoryForm, 'spConnectorId' | 'created'>

type RepositoryCreateForm = Omit<RepositoryForm, 'id' | 'spConnectorId' | 'created'>

type RepositoryCreatePayload = RepositoryCreateForm

export type {
  RepositorySummary,
  RepositoryDetail,
  RepositoryForm,
  RepositoryUpdatePayload,
  RepositoryCreateForm,
  RepositoryCreatePayload,
}
