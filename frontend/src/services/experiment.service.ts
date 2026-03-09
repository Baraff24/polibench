import axios from 'axios'
import type { ExperimentMetrics, ExperimentPublic } from '../models'

const API_URL = import.meta.env.VITE_BACKEND_API_URL

class ExperimentService {
  async getByUuid(uuid: string): Promise<ExperimentPublic> {
    const response = await axios.get(API_URL + `experiments/${uuid}`)
    return response.data
  }

  async getMetrics(uuid: string): Promise<ExperimentMetrics> {
    const response = await axios.get(API_URL + `experiments/${uuid}/metrics`)
    return response.data
  }
}

export default new ExperimentService()
