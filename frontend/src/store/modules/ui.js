/**
 * UI状态管理模块
 * 管理界面相关状态,如侧边栏折叠状态等
 */

// 从localStorage获取保存的侧边栏状态
const getSavedSidebarState = () => {
  try {
    const saved = localStorage.getItem('sidebar_collapsed');
    return saved === 'true';
  } catch (error) {
    return false;
  }
};

const state = {
  // 侧边栏是否折叠
  sidebarCollapsed: getSavedSidebarState(),
};

const mutations = {
  /**
   * 切换侧边栏折叠状态
   */
  TOGGLE_SIDEBAR(state) {
    state.sidebarCollapsed = !state.sidebarCollapsed;
    // 持久化到localStorage
    try {
      localStorage.setItem('sidebar_collapsed', state.sidebarCollapsed.toString());
    } catch (error) {
      console.error('保存侧边栏状态失败:', error);
    }
  },

  /**
   * 设置侧边栏折叠状态
   */
  SET_SIDEBAR_COLLAPSED(state, collapsed) {
    state.sidebarCollapsed = collapsed;
    // 持久化到localStorage
    try {
      localStorage.setItem('sidebar_collapsed', collapsed.toString());
    } catch (error) {
      console.error('保存侧边栏状态失败:', error);
    }
  },
};

const actions = {
  /**
   * 切换侧边栏折叠状态
   */
  toggleSidebar({ commit }) {
    commit('TOGGLE_SIDEBAR');
  },

  /**
   * 设置侧边栏折叠状态
   */
  setSidebarCollapsed({ commit }, collapsed) {
    commit('SET_SIDEBAR_COLLAPSED', collapsed);
  },
};

const getters = {
  /**
   * 获取侧边栏折叠状态
   */
  sidebarCollapsed: (state) => state.sidebarCollapsed,
};

export default {
  namespaced: true,
  state,
  mutations,
  actions,
  getters,
};
