export interface ToolCall {
  name: string;
  args: Record<string, unknown>;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  sources?: string[];
  toolCalls?: ToolCall[];
  isStreaming?: boolean;
}

export interface ChatResponse {
  answer: string;
  sources: string[];
  tool_calls: ToolCall[];
}

export interface IngestResponse {
  status: string;
  job_id: string;
}

export interface JobStatus {
  job_id: string;
  status: 'pending' | 'running' | 'complete' | 'failed';
  files_indexed: number;
  chunks_stored: number;
  error?: string;
}

export interface DocumentsResponse {
  documents: string[];
  total: number;
}

export interface StreamEvent {
  type: 'sources' | 'token' | 'done';
  data?: string | string[];
}
