export type TaskType = 'ranking' | 'rating_prediction' | 'ctr'
export type Visibility = 'public' | 'private'
export type VersionStatus = 'draft' | 'ready' | 'processing' | 'failed'

export interface DatasetSummary {
  uuid: string
  name: string
  task: TaskType
  visibility: Visibility
  versions_count: number
  latest_version: string | null
}

export interface DatasetPublic {
  uuid: string
  name: string
  task: TaskType
  description: string | null
  visibility: Visibility
  team_uuid: string | null
  created_by_user_uuid: string | null
  created_at: string
  versions_count: number
  latest_version: string | null
}

export interface DatasetCreate {
  name: string
  task: TaskType
  description?: string
  visibility?: Visibility
  team_uuid?: string
}

export interface PipelineBlockPublic {
  name: string
  operation: string
  params: Record<string, unknown>
}

export interface DatasetVersionCreate {
  version: string
  release_notes?: string | null
  status?: VersionStatus
  dataset_yaml_raw?: string | null
  version_yaml_raw?: string | null
  pipeline_yaml_raw?: string | null
  characteristics_yaml_raw?: string | null
}

export interface DatasetVersionSummary {
  uuid: string
  dataset_uuid: string
  version: string
  status: VersionStatus
  n_users: number | null
  n_items: number | null
  n_interactions: number | null
  density: number | null
  created_at: string
}

export interface DatasetVersionPublic {
  uuid: string
  dataset_uuid: string
  version: string
  release_notes: string | null
  status: VersionStatus
  pipeline_blocks: PipelineBlockPublic[]
  n_users: number | null
  n_items: number | null
  n_interactions: number | null
  density: number | null
  gini_user: number | null
  gini_item: number | null
  created_at: string
}

export interface SourcePublic {
  uuid: string
  dataset_version_uuid: string
  name: string
  source_type: string
  archive: string | null
  downloadable: boolean
  url: string | null
  checksum: string | null
  checksum_algorithm: string | null
  filename: string | null
  inner_paths: Record<string, unknown> | null
  created_at: string
}

export interface ResourcePublic {
  uuid: string
  dataset_version_uuid: string
  source_uuid: string | null
  name: string
  filename: string | null
  type: string
  format: string | null
  required: boolean
  about: string | null
  schema_definition: Record<string, unknown> | null
  created_at: string
}

export interface DatasetVersionPipelinePublic {
  dataset_version_uuid: string
  blocks: PipelineBlockPublic[]
}

export interface DatasetVersionYamlPublic {
  dataset_version_uuid: string
  kind: string
  content: string
}

export interface DatasetVersionCharacteristicsPreview {
  n_users: number | null
  n_items: number | null
  n_interactions: number | null
  density: number | null
  gini_user: number | null
  gini_item: number | null
}

export interface DatasetVersionPreviewPublic {
  dataset_uuid: string
  requested_version: string
  recognized_dataset_name: string | null
  recognized_version: string | null
  source_count: number
  resource_count: number
  pipeline_steps_count: number
  characteristics: DatasetVersionCharacteristicsPreview
}
