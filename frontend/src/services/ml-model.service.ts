import axios from 'axios'
import type { MLModelCreate, MLModelPublic, MLModelSummary } from '../models'

const API_URL = import.meta.env.VITE_BACKEND_API_URL

class MLModelService {
  async getAll(): Promise<MLModelSummary[]> {
    const response = await axios.get(API_URL + 'ml-models')
    return response.data
  }

  async getByUuid(uuid: string): Promise<MLModelPublic> {
    const response = await axios.get(API_URL + `ml-models/${uuid}`)
    return response.data
  }

  async create(data: MLModelCreate): Promise<MLModelPublic> {
    const response = await axios.post(API_URL + 'ml-models', data)
    return response.data
  }
}

export default new MLModelService()
