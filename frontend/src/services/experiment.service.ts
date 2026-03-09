import axios from 'axios'
import type {
  ExperimentCreate,
  ExperimentMetrics,
  ExperimentPublic,
  MetricsBatchCreate,
} from '../models'

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

  async create(data: ExperimentCreate): Promise<ExperimentPublic> {
    const response = await axios.post(API_URL + 'experiments', data)
    return response.data
  }

  async submitMetrics(uuid: string, data: MetricsBatchCreate): Promise<ExperimentMetrics> {
    const response = await axios.post(API_URL + `experiments/${uuid}/metrics`, data)
    return response.data
  }
}

export default new ExperimentService()
