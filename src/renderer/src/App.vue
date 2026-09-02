<script setup lang="ts">
import type { GlobalThemeOverrides } from 'naive-ui'
import { zhCN, dateZhCN } from 'naive-ui'

// 浅色质感专属定制配色（符合 ui-ux-design 规范）
const themeOverrides: GlobalThemeOverrides = {
  common: {
    primaryColor: '#0284c7',
    primaryColorHover: '#0369a1',
    primaryColorPressed: '#075985',
    primaryColorSuppl: '#38bdf8',
    borderRadius: '10px',
    borderRadiusSmall: '6px'
  },
  Card: {
    borderRadius: '12px',
    boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.04)'
  },
  Button: {
    borderRadiusMedium: '8px',
    borderRadiusSmall: '6px'
  }
}
</script>

<template>
  <n-config-provider :locale="zhCN" :date-locale="dateZhCN" :theme-overrides="themeOverrides">
    <n-loading-bar-provider>
      <n-dialog-provider>
        <n-notification-provider>
          <n-message-provider>
            <router-view />
          </n-message-provider>
        </n-notification-provider>
      </n-dialog-provider>
    </n-loading-bar-provider>
  </n-config-provider>
</template>

<style>
/* 重置与全局基础变量 */
html,
body,
#app {
  width: 100%;
  height: 100%;
  margin: 0;
  padding: 0;
  box-sizing: border-box;
  font-family:
    v-sans,
    system-ui,
    -apple-system,
    BlinkMacSystemFont,
    'Segoe UI',
    Roboto,
    Oxygen,
    Ubuntu,
    Cantarell,
    sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

*,
*::before,
*::after {
  box-sizing: inherit;
}
</style>
