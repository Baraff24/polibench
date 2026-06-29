import type { Direction, Split } from './metric'

export interface LeaderboardEntry {
  experiment_uuid: string
  model_uuid: string
  model_name: string | null
  dataset_uuid: string
  dataset_version_uuid: string
  pipeline_uuid: string | null
  pipeline_code: string | null
  submitted_by_user_uuid: string | null
  submitted_by_display_name: string | null
  submitted_by_email: string | null
  training_config: Record<string, unknown> | null
  status: string | null
  run_name: string | null
  seed: number | null
  created_at: string | null
  split: Split
  metric: string
  k: number | null
  value: number
  direction: Direction
  rank: number | null
}

export interface MultiMetricLeaderboardEntry {
  experiment_uuid: string
  model_uuid: string
  model_name: string | null
  dataset_uuid: string
  dataset_version_uuid: string
  pipeline_uuid: string | null
  pipeline_code: string | null
  submitted_by_user_uuid: string | null
  submitted_by_display_name: string | null
  submitted_by_email: string | null
  training_config: Record<string, unknown> | null
  status: string | null
  run_name: string | null
  seed: number | null
  created_at: string | null
  split: Split
  metrics: Record<string, number>
  directions: Record<string, Direction>
  repo_url: string | null
  rank: number | null
}

export interface LeaderboardQueryPayload {
  dataset_uuid: string
  dataset_version_uuid?: string
  pipeline_uuid?: string
  split: Split
  metrics: string[]
  sort_by?: string
  top_n?: number
  model_uuids?: string[]
  author_uuids?: string[]
  hyperparam_filters?: Record<string, unknown>
}

export interface BestConfigurationQueryPayload {
  dataset_uuid: string
  dataset_version_uuid: string
  pipeline_uuid: string
  split: Split
  metrics: string[]
  target_metric: string
  direction: Direction
  group_by_hyperparams: string[]
  model_uuids?: string[]
  author_uuids?: string[]
  hyperparam_filters?: Record<string, unknown>
}

export interface BestConfigurationGroup {
  model_uuid: string
  model_name: string | null
  submitted_by_user_uuid: string | null
  submitted_by_display_name: string | null
  submitted_by_email: string | null
  hyperparams: Record<string, unknown>
  best_value: number
  mean_value: number
  count: number
  std: number | null
  best_metrics: Record<string, number>
  directions: Record<string, Direction>
  best_pipeline_uuid: string | null
  best_pipeline_code: string | null
  best_experiment_uuid: string | null
  best_run_name: string | null
  best_training_config: Record<string, unknown> | null
}

export interface BestConfigurationResponse {
  dataset_uuid: string
  dataset_version_uuid: string
  pipeline_uuid: string
  split: Split
  metrics: string[]
  target_metric: string
  direction: Direction
  group_by_hyperparams: string[]
  best_group: BestConfigurationGroup | null
  groups: BestConfigurationGroup[]
}
