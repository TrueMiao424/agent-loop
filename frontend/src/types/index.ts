export enum TaskStep {
  RequirementRefinement = 'Requirement_Refinement',
  HumanReview1 = 'Human_Review_1',
  AutoDevelopment = 'Auto_Development',
  HumanReview2 = 'Human_Review_2',
  CommitPush = 'Commit_Push',
}

export enum TaskStatus {
  Init = 'Init',
  Processing = 'Processing',
  Finished = 'Finished',
  Failed = 'Failed',
  Interrupted = 'Interrupted',
  Cancelled = 'Cancelled',
}

export interface Project {
  id: number
  projectName: string
  projectPath: string
  chatGroupId: string
  conventionPath?: string
  gitRemoteUrl?: string
  gitBranch?: string
  gitPushEnabled?: boolean
  createdAt: string
}

export interface TaskStepHistory {
  step: TaskStep
  run: number
  startedAt?: string
  finishedAt?: string
  acceptanceCriteria?: string
  subTasks?: { id: string; title: string; completed: boolean }[]
  affectedFiles?: { predicted_by_agent: string[]; confirmed_by_human: string[] }
  codeDiffs?: { filePath: string; original: string; modified: string; diffText: string }[]
  executionLogs?: string
  reviewOpinion?: string
  rejected?: boolean
  autoReview?: AutoReviewResult
}

export interface AutoReviewResult {
  passed: boolean
  summary: string
  issues: string[]
  skipped?: boolean
  step?: string
  at?: string
}

export interface OpinionHistoryItem {
  step: string
  opinion: string
  reject: boolean
  username: string
  at: string
}

export interface Task {
  id: number
  projectId: number
  title: string
  acceptanceCriteria: string
  currentStep: TaskStep
  currentStatus: TaskStatus
  affectedFiles: { predicted_by_agent: string[]; confirmed_by_human: string[] }
  subTasks: { id: string; title: string; completed: boolean }[]
  executionLogs: string
  codeDiffs?: { filePath: string; original: string; modified: string; diffText: string }[]
  manualEdits?: { id: string; type: string; timestamp: string; content: string }[]
  failReason?: string
  reviewOpinion?: string
  agentMeta?: Record<string, { source?: string; fallback?: boolean; mode?: string; model?: string }>
  reviewAudit?: { action: string; user_id?: number; username: string; at: string }[]
  executionHistory?: TaskStepHistory[]
  autoReview?: AutoReviewResult
  opinionHistory?: OpinionHistoryItem[]
  createdAt: string
  updatedAt: string
}

export interface WebhookMessage {
  id: string
  timestamp: string
  projectId?: number
  taskId?: number
  webhookUrl: string
  title: string
  message: string
  status: string
  isHuman?: boolean
  senderName?: string
}

export interface AgentSession {
  sessionId: string
  taskId: number
  pid: string
  projectName: string
  projectPath: string
  commandLine: string
  inputs: string
  logs: string
  status: string
}

export interface PageResult<T> {
  items: T[]
  total: number
  page: number
  pageSize: number
  processingCount?: number
}

export const STEP_LABELS: Record<string, string> = {
  Requirement_Refinement: '需求拆解',
  Human_Review_1: '人工 Review 1',
  Auto_Development: '自动开发',
  Human_Review_2: '人工 Review 2',
  Commit_Push: '提交发布',
}

export const STATUS_LABELS: Record<string, string> = {
  Init: '待处理',
  Processing: '执行中',
  Finished: '已完成',
  Failed: '失败',
  Interrupted: '已中断',
  Cancelled: '已取消',
}

export const STEP_COLORS: Record<string, string> = {
  Requirement_Refinement: '#6366f1',
  Human_Review_1: '#8b5cf6',
  Auto_Development: '#3b82f6',
  Human_Review_2: '#f59e0b',
  Commit_Push: '#10b981',
}
