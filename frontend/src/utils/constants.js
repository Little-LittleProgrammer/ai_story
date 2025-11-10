// 项目状态常量
export const PROJECT_STATUS = {
  DRAFT: 'draft',
  PROCESSING: 'processing',
  COMPLETED: 'completed',
  FAILED: 'failed',
  PAUSED: 'paused',
};

// 阶段类型常量
export const STAGE_TYPES = {
  REWRITE: 'rewrite',
  STORYBOARD: 'storyboard',
  IMAGE_GENERATION: 'image_generation',
  CAMERA_MOVEMENT: 'camera_movement',
  VIDEO_GENERATION: 'video_generation',
};

// 阶段状态常量
export const STAGE_STATUS = {
  PENDING: 'pending',
  RUNNING: 'running',
  COMPLETED: 'completed',
  FAILED: 'failed',
  SKIPPED: 'skipped',
};

// 模型提供商类型
export const PROVIDER_TYPES = {
  LLM: 'llm',
  TEXT2IMAGE: 'text2image',
  IMAGE2VIDEO: 'image2video',
};

// 负载均衡策略
export const LOAD_BALANCE_STRATEGIES = {
  ROUND_ROBIN: 'round_robin',
  RANDOM: 'random',
  WEIGHTED: 'weighted',
  LEAST_LOADED: 'least_loaded',
};

// 运镜类型
export const CAMERA_MOVEMENT_TYPES = {
  STATIC: 'static',
  ZOOM_IN: 'zoom_in',
  ZOOM_OUT: 'zoom_out',
  PAN_LEFT: 'pan_left',
  PAN_RIGHT: 'pan_right',
  TILT_UP: 'tilt_up',
  TILT_DOWN: 'tilt_down',
};
