import apiClient from './apiClient';

export default {
  // 获取文案改写结果
  getRewrite(projectId) {
    return apiClient.get(`/content/rewrites/${projectId}/`);
  },

  // 获取分镜列表
  getStoryboards(projectId) {
    return apiClient.get(`/content/storyboards/`, {
      params: { project_id: projectId },
    });
  },

  // 获取单个分镜
  getStoryboard(id) {
    return apiClient.get(`/content/storyboards/${id}/`);
  },

  // 获取生成的图片
  getGeneratedImages(storyboardId) {
    return apiClient.get(`/content/generated-images/`, {
      params: { storyboard_id: storyboardId },
    });
  },

  // 获取运镜参数
  getCameraMovement(storyboardId) {
    return apiClient.get(`/content/camera-movements/${storyboardId}/`);
  },

  // 获取生成的视频
  getGeneratedVideos(storyboardId) {
    return apiClient.get(`/content/generated-videos/`, {
      params: { storyboard_id: storyboardId },
    });
  },

  // 重新生成图片
  regenerateImage(storyboardId) {
    return apiClient.post(`/content/storyboards/${storyboardId}/regenerate-image/`);
  },

  // 重新生成视频
  regenerateVideo(storyboardId) {
    return apiClient.post(`/content/storyboards/${storyboardId}/regenerate-video/`);
  },
};
