import axios from 'axios'
import type { LeaderboardEntry, MultiMetricLeaderboardEntry, Split } from '../models'

const API_URL = import.meta.env.VITE_BACKEND_API_URL

class LeaderboardService {
  async get(
    datasetUuid: string,
    metric: string,
    split: Split,
    topN: number = 10,
    datasetVersionUuid?: string,
    pipelineUuid?: string,
  ): Promise<LeaderboardEntry[]> {
    const params = new URLSearchParams({
      dataset_uuid: datasetUuid,
      metric,
      split,
      top_n: String(topN),
    })
    if (datasetVersionUuid) {
      params.set('dataset_version_uuid', datasetVersionUuid)
    }
    if (pipelineUuid) {
      params.set('pipeline_uuid', pipelineUuid)
    }
    const response = await axios.get(API_URL + `leaderboard?${params}`)
    return response.data
  }

  async getMultiMetric(
    datasetUuid: string,
    metrics: string[],
    split: Split,
    sortBy: string,
    topN: number = 20,
    datasetVersionUuid?: string,
    pipelineUuid?: string,
  ): Promise<MultiMetricLeaderboardEntry[]> {
    const params = new URLSearchParams({
      dataset_uuid: datasetUuid,
      metrics: metrics.join(','),
      split,
      sort_by: sortBy,
      top_n: String(topN),
    })
    if (datasetVersionUuid) {
      params.set('dataset_version_uuid', datasetVersionUuid)
    }
    if (pipelineUuid) {
      params.set('pipeline_uuid', pipelineUuid)
    }
    const response = await axios.get(API_URL + `leaderboard/multi?${params}`)
    return response.data
  }
}

export default new LeaderboardService()
