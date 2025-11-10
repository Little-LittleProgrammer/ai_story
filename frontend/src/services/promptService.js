import apiClient from './apiClient';

export default {
  // 获取提示词集列表
  getTemplateSets(params) {
    return apiClient.get('/prompts/template-sets/', { params });
  },

  // 获取提示词集详情
  getTemplateSet(id) {
    return apiClient.get(`/prompts/template-sets/${id}/`);
  },

  // 创建提示词集
  createTemplateSet(data) {
    return apiClient.post('/prompts/template-sets/', data);
  },

  // 更新提示词集
  updateTemplateSet(id, data) {
    return apiClient.patch(`/prompts/template-sets/${id}/`, data);
  },

  // 删除提示词集
  deleteTemplateSet(id) {
    return apiClient.delete(`/prompts/template-sets/${id}/`);
  },

  // 获取提示词模板列表
  getTemplates(setId) {
    return apiClient.get(`/prompts/template-sets/${setId}/templates/`);
  },

  // 创建提示词模板
  createTemplate(data) {
    return apiClient.post('/prompts/templates/', data);
  },

  // 更新提示词模板
  updateTemplate(id, data) {
    return apiClient.patch(`/prompts/templates/${id}/`, data);
  },

  // 删除提示词模板
  deleteTemplate(id) {
    return apiClient.delete(`/prompts/templates/${id}/`);
  },
};
