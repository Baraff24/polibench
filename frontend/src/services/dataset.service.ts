import axios from 'axios'
import type {
  DatasetCreate,
  DatasetPublic,
  DatasetSummary,
  ExperimentSummary,
  PipelineCreate,
  PipelinePreviewPublic,
  PipelinePublic,
  PipelineSummary,
  PipelineYamlPublic,
  DatasetVersionCreate,
  DatasetVersionPreviewPublic,
  DatasetVersionPublic,
  DatasetVersionSummary,
  DatasetVersionYamlPublic,
  ResourcePublic,
  SourcePublic,
} from '../models'

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

  async getVersions(datasetUuid: string): Promise<DatasetVersionSummary[]> {
    const response = await axios.get(API_URL + `datasets/${datasetUuid}/versions`)
    return response.data
  }

  async createVersion(
    datasetUuid: string,
    data: DatasetVersionCreate,
  ): Promise<DatasetVersionPublic> {
    const response = await axios.post(API_URL + `datasets/${datasetUuid}/versions`, data)
    return response.data
  }

  async previewVersion(
    datasetUuid: string,
    data: DatasetVersionCreate,
  ): Promise<DatasetVersionPreviewPublic> {
    const response = await axios.post(API_URL + `datasets/${datasetUuid}/versions/preview`, data)
    return response.data
  }

  async getVersionByUuid(versionUuid: string): Promise<DatasetVersionPublic> {
    const response = await axios.get(API_URL + `dataset-versions/${versionUuid}`)
    return response.data
  }

  async getVersionSources(versionUuid: string): Promise<SourcePublic[]> {
    const response = await axios.get(API_URL + `dataset-versions/${versionUuid}/sources`)
    return response.data
  }

  async getVersionResources(versionUuid: string): Promise<ResourcePublic[]> {
    const response = await axios.get(API_URL + `dataset-versions/${versionUuid}/resources`)
    return response.data
  }

  async getVersionPipelines(versionUuid: string): Promise<PipelineSummary[]> {
    const response = await axios.get(API_URL + `dataset-versions/${versionUuid}/pipelines`)
    return response.data
  }

  async createPipeline(versionUuid: string, data: PipelineCreate): Promise<PipelinePublic> {
    const response = await axios.post(API_URL + `dataset-versions/${versionUuid}/pipelines`, data)
    return response.data
  }

  async previewPipeline(
    versionUuid: string,
    data: PipelineCreate,
  ): Promise<PipelinePreviewPublic> {
    const response = await axios.post(
      API_URL + `dataset-versions/${versionUuid}/pipelines/preview`,
      data,
    )
    return response.data
  }

  async getPipelineByUuid(pipelineUuid: string): Promise<PipelinePublic> {
    const response = await axios.get(API_URL + `pipelines/${pipelineUuid}`)
    return response.data
  }

  async getPipelineYaml(pipelineUuid: string): Promise<PipelineYamlPublic> {
    const response = await axios.get(API_URL + `pipelines/${pipelineUuid}/yaml`)
    return response.data
  }

  async downloadPipelineYamlRaw(pipelineUuid: string): Promise<string> {
    const response = await axios.get(API_URL + `pipelines/${pipelineUuid}/yaml/raw`, {
      responseType: 'text',
      transformResponse: [(data) => data],
    })
    return response.data as string
  }

  async getPipelineExperiments(pipelineUuid: string): Promise<ExperimentSummary[]> {
    const response = await axios.get(API_URL + `pipelines/${pipelineUuid}/experiments`)
    return response.data
  }

  async getVersionYaml(versionUuid: string, kind: string): Promise<DatasetVersionYamlPublic> {
    const response = await axios.get(API_URL + `dataset-versions/${versionUuid}/yaml/${kind}`)
    return response.data
  }

  async downloadVersionYamlRaw(versionUuid: string, kind: string): Promise<string> {
    const response = await axios.get(API_URL + `dataset-versions/${versionUuid}/yaml/${kind}/raw`, {
      responseType: 'text',
      transformResponse: [(data) => data],
    })
    return response.data as string
  }
}

export default new DatasetService()
