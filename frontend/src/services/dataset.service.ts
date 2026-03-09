import axios from 'axios'
import type { DatasetCreate, DatasetPublic, DatasetSummary } from '../models'

const API_URL = import.meta.env.VITE_BACKEND_API_URL

class DatasetService {
  async getAll(): Promise<DatasetSummary[]> {
    const response = await axios.get(API_URL + 'datasets')
    return response.data
  }

  async getByUuid(uuid: string): Promise<DatasetPublic> {
    const response = await axios.get(API_URL + `datasets/${uuid}`)
    return response.data
  }

  async create(data: DatasetCreate): Promise<DatasetPublic> {
    const response = await axios.post(API_URL + 'datasets', data)
    return response.data
  }
}

export default new DatasetService()
