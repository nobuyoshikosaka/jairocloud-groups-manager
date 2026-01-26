export type ValidationStatus = 'ok' | 'warning' | 'error'
export type OperationType = 'create' | 'update' | 'delete' | 'skip'
export type UploadResultStatus = 'success' | 'failed'
export type UploadResultOperation = 'create' | 'update' | 'delete'

export interface ValidationResult {
  row: number
  operation: OperationType
  status: ValidationStatus
  name: string
  eppn: string
  groups: string[]
  message?: string
}

export interface UnmatchedUser {
  id: number
  name: string
  eppn: string
  groups: string[]
}

export interface UploadResult {
  operation: UploadResultOperation
  status: UploadResultStatus
  name: string
  eppn: string
  groups: string[]
  message?: string
  timestamp: string
}
