import apiClient from './apiClient';

export default {
  // 获取模型提供商列表
  getProviders(type = null) {
    const params = type ? { provider_type: type } : {};
    return apiClient.get('/models/providers/', { params });
  },

  // 获取模型提供商详情
  getProvider(id) {
    return apiClient.get(`/models/providers/${id}/`);
  },

  // 创建模型提供商
  createProvider(data) {
    return apiClient.post('/models/providers/', data);
  },

  // 更新模型提供商
  updateProvider(id, data) {
    return apiClient.patch(`/models/providers/${id}/`, data);
  },

  // 删除模型提供商
  deleteProvider(id) {
    return apiClient.delete(`/models/providers/${id}/`);
  },

  // 获取使用日志
  getUsageLogs(params) {
    return apiClient.get('/models/usage-logs/', { params });
  },

  // 获取使用统计
  getUsageStats(params) {
    return apiClient.get('/models/usage-stats/', { params });
  },
};
