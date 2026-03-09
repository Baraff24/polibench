export type TaskType = 'ranking' | 'rating_prediction'
export type Visibility = 'public' | 'private'

export interface Splits {
  train: number | null
  test: number | null
  validation: number | null
}

export interface DatasetSummary {
  uuid: string
  name: string
  version: string
  task: TaskType
  visibility: Visibility
}

export interface DatasetPublic {
  uuid: string
  name: string
  version: string
  task: TaskType
  description: string | null
  visibility: Visibility
  splits: Splits | null
  team_uuid: string | null
  created_by_user_uuid: string | null
  created_at: string
}

export interface DatasetCreate {
  name: string
  version: string
  task: TaskType
  description?: string
  visibility?: Visibility
  splits?: Splits
  team_uuid?: string
}
