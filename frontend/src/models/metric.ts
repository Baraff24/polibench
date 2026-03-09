export type Split = 'validation' | 'test'
export type Direction = 'max' | 'min'

export interface MetricCreate {
  split: Split
  metric: string
  k?: number | null
  value: number
  direction: Direction
}

export interface MetricsBatchCreate {
  experiment_uuid: string
  metrics: MetricCreate[]
}

export interface MetricPublic {
  uuid: string
  experiment_uuid: string
  dataset_uuid: string
  model_uuid: string
  split: Split
  metric: string
  k: number | null
  value: number
  direction: Direction
  computed_at: string
}

export interface ExperimentMetrics {
  experiment_uuid: string
  metrics_by_split: Record<Split, MetricPublic[]>
}
