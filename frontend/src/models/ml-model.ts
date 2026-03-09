export interface MLModelSummary {
  uuid: string
  name: string
  family: string | null
  paper_url: string | null
}

export interface MLModelPublic {
  uuid: string
  name: string
  family: string | null
  paper_url: string | null
  implementation: string | null
  hyperparams: Record<string, unknown> | null
  created_by_user_uuid: string | null
  created_at: string
}

export interface MLModelCreate {
  name: string
  family?: string
  paper_url?: string
  implementation?: string
  hyperparams?: Record<string, unknown>
}
