import { request } from '../request';

export const documentsApi = {
  // Get all documents with optional status filter
  getDocuments: async (statusFilter = null) => {
    const params = statusFilter ? { status_filter: statusFilter } : {};
    const response = await request.get('/api/documents', { params });
    return response.data;
  },

  // Get document detail with content
  getDocument: async (filename) => {
    const response = await request.get(`/api/documents/${encodeURIComponent(filename)}`);
    return response.data;
  },

  // Sync documents from directory
  syncDocuments: async () => {
    const response = await request.post('/api/documents/sync');
    return response.data;
  },

  // Reindex specific documents
  reindexDocuments: async (filenames = []) => {
    const response = await request.post('/api/reindex/selective', { filenames });
    return response.data;
  },

  // Cleanup deleted documents
  cleanupDeletedDocuments: async () => {
    const response = await request.delete('/api/documents/cleanup');
    return response.data;
  },
};
