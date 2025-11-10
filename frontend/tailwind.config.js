module.exports = {
  content: [
    './public/**/*.html',
    './src/**/*.{vue,js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {},
  },
  plugins: [require('daisyui')],
  daisyui: {
    themes: ['light', 'dark', 'cupcake'], // 启用多个主题
    darkTheme: 'dark', // 默认暗色主题
    base: true, // 应用基础样式
    styled: true, // 应用组件样式
    utils: true, // 添加工具类
    prefix: '', // 添加前缀（如需要）
    logs: true, // 显示日志
  },
};
