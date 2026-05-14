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

export interface Environment {
  id: number
  name: string
  label: string
  base_url: string
  timeout: number
  auth_type: string
  auth_token: string
  auth_username: string
  auth_password: string
  headers: string
  variables: string
  description: string
  is_active: number
  created_at: string | null
  updated_at: string | null
}

export interface EnvironmentCreate {
  name: string
  label?: string
  base_url?: string
  timeout?: number
  auth_type?: string
  auth_token?: string
  auth_username?: string
  auth_password?: string
  headers?: string
  variables?: string
  description?: string
}

export const environmentApi = {
  list: () => api.get<Environment[]>('/environments'),
  get: (id: number) => api.get<Environment>(`/environments/${id}`),
  create: (data: EnvironmentCreate) => api.post<Environment>('/environments', data),
  update: (id: number, data: Partial<EnvironmentCreate>) => api.put<Environment>(`/environments/${id}`, data),
  delete: (id: number) => api.delete(`/environments/${id}`),
  clone: (id: number, newName: string) => api.post<Environment>(`/environments/${id}/clone?new_name=${newName}`),
}

export interface Worker {
  id: number
  worker_id: string
  name: string
  host: string
  port: number
  status: string
  max_concurrency: number
  current_tasks: number
  tags: string
  last_heartbeat: string | null
  registered_at: string | null
}

export interface TaskShard {
  id: number
  execution_id: number
  worker_id: string
  shard_index: number
  total_shards: number
  case_paths: string
  status: string
  exit_code: number | null
  total_cases: number
  passed_cases: number
  failed_cases: number
  error_cases: number
  elapsed_ms: number
  started_at: string | null
  finished_at: string | null
}

export const workerApi = {
  list: () => api.get<Worker[]>('/workers'),
  remove: (workerId: string) => api.delete(`/workers/${workerId}`),
  shards: (executionId: number) => api.get<TaskShard[]>(`/workers/shards/${executionId}`),
  dispatch: (data: { case_ids?: number[]; base_url?: string; env_name?: string; tags?: string; shard_count?: number }) =>
    api.post('/workers/dispatch', data),
}

export interface MockRule {
  id: number
  name: string
  method: string
  path: string
  match_headers: string
  match_query: string
  match_body: string
  response_status: number
  response_headers: string
  response_body: string
  response_delay_ms: number
  priority: number
  is_active: number
  hit_count: number
  description: string
  created_at: string | null
  updated_at: string | null
}

export interface MockRuleCreate {
  name: string
  method?: string
  path: string
  match_headers?: string
  match_query?: string
  match_body?: string
  response_status?: number
  response_headers?: string
  response_body?: string
  response_delay_ms?: number
  priority?: number
  description?: string
}

export const mockApi = {
  list: () => api.get<MockRule[]>('/mocks'),
  get: (id: number) => api.get<MockRule>(`/mocks/${id}`),
  create: (data: MockRuleCreate) => api.post<MockRule>('/mocks', data),
  update: (id: number, data: Partial<MockRuleCreate>) => api.put<MockRule>(`/mocks/${id}`, data),
  delete: (id: number) => api.delete(`/mocks/${id}`),
  generate: (caseId: number) => api.post<MockRule[]>('/mocks/generate', { case_id: caseId }),
  resetHits: (id: number) => api.post(`/mocks/${id}/reset-hits`),
}

export interface Benchmark {
  id: number
  name: string
  target_url: string
  method: string
  headers: string
  body: string
  concurrency: number
  total_requests: number
  duration_seconds: number
  status: string
  total_sent: number
  success_count: number
  fail_count: number
  avg_latency_ms: number
  p50_latency_ms: number
  p90_latency_ms: number
  p95_latency_ms: number
  p99_latency_ms: number
  min_latency_ms: number
  max_latency_ms: number
  rps: number
  elapsed_ms: number
  error_distribution: string
  started_at: string | null
  finished_at: string | null
  created_at: string | null
}

export interface BenchmarkCreate {
  name: string
  target_url: string
  method?: string
  headers?: string
  body?: string
  concurrency?: number
  total_requests?: number
  duration_seconds?: number
}

export const benchmarkApi = {
  list: () => api.get<Benchmark[]>('/benchmarks'),
  get: (id: number) => api.get<Benchmark>(`/benchmarks/${id}`),
  create: (data: BenchmarkCreate) => api.post<Benchmark>('/benchmarks', data),
  delete: (id: number) => api.delete(`/benchmarks/${id}`),
}

export interface Pipeline {
  id: number
  name: string
  platform: string
  trigger_type: string
  cron_expr: string
  webhook_secret: string
  case_filter_tags: string
  env_name: string
  base_url: string
  notify_on_fail: number
  notify_webhook: string
  badge_enabled: number
  last_status: string
  last_run_at: string | null
  is_active: number
  description: string
  created_at: string | null
  updated_at: string | null
}

export interface PipelineCreate {
  name: string
  platform?: string
  trigger_type?: string
  cron_expr?: string
  webhook_secret?: string
  case_filter_tags?: string
  env_name?: string
  base_url?: string
  notify_on_fail?: number
  notify_webhook?: string
  badge_enabled?: number
  description?: string
}

export interface PipelineRun {
  id: number
  pipeline_id: number
  trigger_source: string
  commit_sha: string
  branch: string
  status: string
  total_cases: number
  passed_cases: number
  failed_cases: number
  elapsed_ms: number
  execution_id: number | null
  started_at: string | null
  finished_at: string | null
  created_at: string | null
}

export const pipelineApi = {
  list: () => api.get<Pipeline[]>('/pipelines'),
  get: (id: number) => api.get<Pipeline>(`/pipelines/${id}`),
  create: (data: PipelineCreate) => api.post<Pipeline>('/pipelines', data),
  update: (id: number, data: Partial<PipelineCreate>) => api.put<Pipeline>(`/pipelines/${id}`, data),
  delete: (id: number) => api.delete(`/pipelines/${id}`),
  trigger: (id: number, data?: { commit_sha?: string; branch?: string; trigger_source?: string }) =>
    api.post<PipelineRun>(`/pipelines/${id}/trigger`, data || {}),
  runs: (id: number) => api.get<PipelineRun[]>(`/pipelines/${id}/runs`),
}

export interface UserInfo {
  id: number
  username: string
  display_name: string
  email: string
  role: string
  team_id: number | null
  is_active: number
  last_login_at: string | null
  created_at: string | null
}

export interface TeamInfo {
  id: number
  name: string
  description: string
  max_members: number
  created_at: string | null
}

export const authApi = {
  login: (data: { username: string; password: string }) => api.post<{ token: string; user: UserInfo }>('/auth/login', data),
  logout: () => api.post('/auth/logout'),
  me: () => api.get<UserInfo>('/auth/me'),
}

export const userApi = {
  list: () => api.get<UserInfo[]>('/users'),
  create: (data: { username: string; password: string; display_name?: string; email?: string; role?: string; team_id?: number }) =>
    api.post<UserInfo>('/users', data),
  update: (id: number, data: Partial<{ display_name: string; email: string; role: string; team_id: number; is_active: number }>) =>
    api.put<UserInfo>(`/users/${id}`, data),
  delete: (id: number) => api.delete(`/users/${id}`),
}

export const teamApi = {
  list: () => api.get<TeamInfo[]>('/teams'),
  create: (data: { name: string; description?: string; max_members?: number }) => api.post<TeamInfo>('/teams', data),
  update: (id: number, data: Partial<{ name: string; description: string; max_members: number }>) =>
    api.put<TeamInfo>(`/teams/${id}`, data),
  delete: (id: number) => api.delete(`/teams/${id}`),
}

export default api
