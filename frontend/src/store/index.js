import Vue from 'vue';
import Vuex from 'vuex';

import auth from './modules/auth';
import projects from './modules/projects';
import prompts from './modules/prompts';
import models from './modules/models';
import content from './modules/content';
import ui from './modules/ui';

Vue.use(Vuex);

export default new Vuex.Store({
  state: {
    loading: false,
    error: null,
  },
  mutations: {
    SET_LOADING(state, loading) {
      state.loading = loading;
    },
    SET_ERROR(state, error) {
      state.error = error;
    },
  },
  actions: {
    setLoading({ commit }, loading) {
      commit('SET_LOADING', loading);
    },
    setError({ commit }, error) {
      commit('SET_ERROR', error);
    },
  },
  modules: {
    auth,
    projects,
    prompts,
    models,
    content,
    ui,
  },
});
