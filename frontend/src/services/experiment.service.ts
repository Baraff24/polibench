import axios from 'axios'
import type {
  ExperimentCreate,
  ExperimentMetrics,
  ExperimentPublic,
  ExperimentSummary,
  MetricImportPublic,
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

  // Legacy direct submission endpoint (kept during migration).
  async submitMetrics(uuid: string, data: MetricsBatchCreate): Promise<ExperimentMetrics> {
    const response = await axios.post(API_URL + `experiments/${uuid}/metrics`, data)
    return response.data
  }

  async importMetricsCsv(uuid: string, file: File): Promise<MetricImportPublic> {
    const formData = new FormData()
    formData.append('file', file)
    const response = await axios.post(API_URL + `experiments/${uuid}/metric-import`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return response.data
  }

  async listMetricImports(uuid: string): Promise<MetricImportPublic[]> {
    const response = await axios.get(API_URL + `experiments/${uuid}/metric-imports`)
    return response.data
  }

  async listByDatasetVersion(datasetVersionUuid: string): Promise<ExperimentSummary[]> {
    const response = await axios.get(
      API_URL + `dataset-versions/${datasetVersionUuid}/experiments`,
    )
    return response.data
  }
}

export default new ExperimentService()
