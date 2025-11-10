import contentService from '@/services/contentService';

const state = {
  storyboards: [],
  generatedImages: [],
  generatedVideos: [],
};

const mutations = {
  SET_STORYBOARDS(state, storyboards) {
    state.storyboards = storyboards;
  },
  SET_GENERATED_IMAGES(state, images) {
    state.generatedImages = images;
  },
  SET_GENERATED_VIDEOS(state, videos) {
    state.generatedVideos = videos;
  },
};

const actions = {
  async fetchStoryboards({ commit }, projectId) {
    try {
      const storyboards = await contentService.getStoryboards(projectId);
      commit('SET_STORYBOARDS', storyboards);
      return storyboards;
    } catch (error) {
      console.error('Failed to fetch storyboards:', error);
      throw error;
    }
  },

  async fetchGeneratedImages({ commit }, storyboardId) {
    try {
      const images = await contentService.getGeneratedImages(storyboardId);
      commit('SET_GENERATED_IMAGES', images);
      return images;
    } catch (error) {
      console.error('Failed to fetch generated images:', error);
      throw error;
    }
  },

  async fetchGeneratedVideos({ commit }, storyboardId) {
    try {
      const videos = await contentService.getGeneratedVideos(storyboardId);
      commit('SET_GENERATED_VIDEOS', videos);
      return videos;
    } catch (error) {
      console.error('Failed to fetch generated videos:', error);
      throw error;
    }
  },
};

export default {
  namespaced: true,
  state,
  mutations,
  actions,
};
