<template>
  <div class="status-badge">
    <div :class="['badge', statusInfo.badgeClass]">
      {{ statusInfo.label }}
    </div>
  </div>
</template>

<script>
import { getProjectStatusTag, getStageStatusTag } from '@/utils/helpers';

export default {
  name: 'StatusBadge',
  props: {
    status: {
      type: String,
      required: true,
    },
    type: {
      type: String,
      default: 'project', // 'project' or 'stage'
    },
  },
  computed: {
    statusInfo() {
      const info = this.type === 'stage'
        ? getStageStatusTag(this.status)
        : getProjectStatusTag(this.status);

      // 将 Element UI 的 type 映射到 daisyUI 的 badge 类
      const typeMapping = {
        success: 'badge-success',
        warning: 'badge-warning',
        danger: 'badge-error',
        info: 'badge-info',
        primary: 'badge-primary',
      };

      return {
        ...info,
        badgeClass: typeMapping[info.type] || 'badge-ghost',
      };
    },
  },
};
</script>

<style scoped>
.status-badge {
  display: inline-block;
}
</style>
