import { request } from '../request';

interface ChatRequest {
  message: string;
  conversation_id?: string | null;
}

interface ChatResponse {
  answer: string;
  sources: any[];
  conversation_id: string;
}

interface HealthResponse {
  status: string;
}

interface StatsResponse {
  [key: string]: any;
}

/**
 * 发送聊天消息
 */
export const chat = async (
  message: string,
  conversationId: string | null = null,
): Promise<ChatResponse> => {
  const response = await request.post<ChatResponse>('/api/chat', {
    message,
    conversation_id: conversationId,
  });
  return response.data;
};

/**
 * 健康检查
 */
export const getHealth = async (): Promise<HealthResponse> => {
  const response = await request.get<HealthResponse>('/api/health');
  return response.data;
};

/**
 * 获取统计信息
 */
export const getStats = async (): Promise<StatsResponse> => {
  const response = await request.get<StatsResponse>('/api/stats');
  return response.data;
};

/**
 * 清除对话
 */
export const clearConversation = async (conversationId: string): Promise<any> => {
  const response = await request.delete(`/api/chat/${conversationId}`);
  return response.data;
};
