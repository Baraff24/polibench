import type { Direction, Split } from './metric'

export interface LeaderboardEntry {
  experiment_uuid: string
  model_uuid: string
  model_name: string | null
  dataset_uuid: string
  split: Split
  metric: string
  k: number | null
  value: number
  direction: Direction
  rank: number | null
}
