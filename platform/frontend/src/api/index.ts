import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
})

export interface TestCase {
  id: number
  name: string
  folder: string
  filename: string
  tags: string
  priority: string
  status: string
  last_run_at: string | null
  content?: string
  created_at: string | null
}

export interface FolderNode {
  label: string
  path: string
  children: FolderNode[]
}

export interface CaseCreate {
  name: string
  folder?: string
  tags?: string
  priority?: string
  content?: string
}

export const caseApi = {
  list: (params?: Record<string, string>) => api.get<TestCase[]>('/cases', { params }),
  get: (id: number) => api.get<TestCase>(`/cases/${id}`),
  create: (data: CaseCreate) => api.post<TestCase>('/cases', data),
  update: (id: number, data: Partial<CaseCreate>) => api.put<TestCase>(`/cases/${id}`, data),
  delete: (id: number) => api.delete(`/cases/${id}`),
  folders: () => api.get<FolderNode[]>('/cases/folders'),
}

export interface Execution {
  id: number
  run_id: string
  case_name: string
  status: string
  exit_code: number | null
  total_cases: number
  passed_cases: number
  failed_cases: number
  elapsed_ms: number
  started_at: string | null
  finished_at: string | null
  stdout?: string
  stderr?: string
  report_dir?: string
}

export interface ExecutionCreate {
  case_id?: number
  case_path?: string
  base_url?: string
  env_name?: string
  tags?: string
  workers?: number
  variables?: Record<string, string>
}

export const executionApi = {
  list: (params?: Record<string, string>) => api.get<Execution[]>('/executions', { params }),
  get: (id: number) => api.get<Execution>(`/executions/${id}`),
  create: (data: ExecutionCreate) => api.post<Execution>('/executions', data),
  report: (id: number) => api.get(`/executions/${id}/report`),
}

export default api
