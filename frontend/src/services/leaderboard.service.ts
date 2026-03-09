import axios from 'axios'
import type { LeaderboardEntry, Split } from '../models'

const API_URL = import.meta.env.VITE_BACKEND_API_URL

class LeaderboardService {
  async get(
    datasetUuid: string,
    metric: string,
    split: Split,
    topN: number = 10,
  ): Promise<LeaderboardEntry[]> {
    const params = new URLSearchParams({
      dataset_uuid: datasetUuid,
      metric,
      split,
      top_n: String(topN),
    })
    const response = await axios.get(API_URL + `leaderboard?${params}`)
    return response.data
  }
}

export default new LeaderboardService()
