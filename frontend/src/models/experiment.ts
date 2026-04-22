export type Status = 'queued' | 'running' | 'finished' | 'failed'

export interface CodeInfo {
  git_commit: string | null
  repo_url: string | null
  docker_image: string | null
}

export interface Artifacts {
  logs_url: string | null
  model_path: string | null
  predictions_path: string | null
}

export interface ExperimentCreate {
  dataset_version_uuid?: string
  dataset_uuid?: string
  model_uuid: string
  team_uuid?: string | null
  run_name?: string | null
  seed?: number | null
  notes?: string | null
  training_config?: Record<string, unknown> | null
  code?: CodeInfo | null
}

export interface ExperimentPublic {
  uuid: string
  dataset_uuid: string
  dataset_version_uuid: string
  model_uuid: string
  team_uuid: string | null
  submitted_by_user_uuid: string | null
  run_name: string | null
  status: Status
  seed: number | null
  notes: string | null
  training_config: Record<string, unknown> | null
  code: CodeInfo | null
  artifacts: Artifacts | null
  created_at: string
  finished_at: string | null
}

export interface ExperimentSummary {
  uuid: string
  dataset_uuid: string
  dataset_version_uuid: string
  model_uuid: string
  model_name: string | null
  run_name: string | null
  status: Status
  created_at: string
}
