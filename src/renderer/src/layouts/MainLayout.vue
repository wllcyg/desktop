<script setup lang="ts">
import { h, ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter, useRoute, RouterLink } from 'vue-router'
import type { MenuOption } from 'naive-ui'
import { NTag, useDialog, useNotification } from 'naive-ui'

const router = useRouter()
const route = useRoute()
const dialog = useDialog()
const notification = useNotification()

// 全局自动更新监听与弹窗提示
const onUpdaterMessage = (_: unknown, data: { channel: string; text: string; data?: any }) => {
  if (data.channel === 'available') {
    notification.info({
      title: '发现新版本',
      content: `${data.text}，正在后台静默下载更新包...`,
      duration: 6000
    })
  } else if (data.channel === 'downloaded') {
    dialog.success({
      title: '✨ 新版本已就绪',
      content: `${data.text}。您可以立即重启软件体验最新功能，或在退出软件时自动完成更新。`,
      positiveText: '立即重启更新',
      negativeText: '稍后更新',
      onPositiveClick: () => {
        window.electron?.ipcRenderer?.invoke('updater:quit-and-install')
      }
    })
  }
}

onMounted(() => {
  window.electron?.ipcRenderer?.on('updater:message', onUpdaterMessage)
})

onUnmounted(() => {
  window.electron?.ipcRenderer?.removeAllListeners('updater:message')
})

// 选中的菜单项
const activeKey = computed(() => {
  if (route.path === '/') return 'home'
  return route.path.replace(/^\//, '')
})

// 侧边栏折叠状态
const collapsed = ref(false)

// 构建菜单项辅助函数
const renderLabel = (label: string, routePath: string, isMvp = false) => {
  return () =>
    h(
      'div',
      {
        style: 'display: flex; align-items: center; justify-content: space-between; width: 100%;'
      },
      [
        h(RouterLink, { to: routePath }, { default: () => label }),
        isMvp
          ? h(
              NTag,
              { size: 'tiny', type: 'success', round: true, style: 'margin-left: 8px;' },
              { default: () => 'MVP' }
            )
          : null
      ]
    )
}

const menuOptions: MenuOption[] = [
  {
    label: () => h(RouterLink, { to: '/' }, { default: () => '工作台首页' }),
    key: 'home'
  },
  {
    type: 'divider',
    key: 'd1'
  },
  {
    label: '一、图片/文档处理',
    key: 'cat-image-doc',
    children: [
      {
        label: renderLabel('图片去水印', '/image-doc/watermark', true),
        key: 'image-doc/watermark'
      },
      {
        label: renderLabel('OCR文字/公式识别', '/image-doc/ocr', true),
        key: 'image-doc/ocr'
      },
      {
        label: renderLabel('PDF合并/拆分', '/image-doc/pdf-tool'),
        key: 'image-doc/pdf-tool'
      },
      {
        label: renderLabel('图片工作台', '/image-doc/studio', true),
        key: 'image-doc/studio'
      }
    ]
  },
  {
    label: '二、批量处理',
    key: 'cat-batch',
    children: [
      {
        label: renderLabel('文件批量重命名', '/batch/rename', true),
        key: 'batch/rename'
      }
    ]
  },
  {
    type: 'divider',
    key: 'd2'
  },
  {
    label: () => h(RouterLink, { to: '/settings/models' }, { default: () => '🧩 AI本地模型管理' }),
    key: 'settings/models'
  },
  {
    label: () => h(RouterLink, { to: '/settings' }, { default: () => '⚙️ 系统设置与关于' }),
    key: 'settings'
  }
]
</script>

<template>
  <div class="layout-wrapper">
    <!-- 左侧导航栏 -->
    <aside class="sidebar" :class="{ 'is-collapsed': collapsed }">
      <!-- 品牌标识 -->
      <div class="brand-header" @click="router.push('/')">
        <div class="brand-logo">
          <span class="logo-flask">⚗️</span>
        </div>
        <div v-if="!collapsed" class="brand-info">
          <span class="brand-title">工具箱</span>
          <span class="brand-subtitle">高效桌面助手</span>
        </div>
      </div>

      <!-- 菜单区 -->
      <div class="menu-container">
        <n-menu
          :value="activeKey"
          :collapsed="collapsed"
          :collapsed-width="64"
          :collapsed-icon-size="20"
          :options="menuOptions"
          :default-expanded-keys="['cat-image-doc', 'cat-batch', 'cat-chemistry']"
          accordion
        />
      </div>

      <!-- 底部操作区 -->
      <div class="sidebar-footer">
        <n-text depth="3" class="version-text">v0.1.2</n-text>
      </div>
    </aside>

    <!-- 右侧主展示区 -->
    <main class="main-content">
      <div class="content-scrollable">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </div>
    </main>
  </div>
</template>

<style scoped>
.layout-wrapper {
  display: flex;
  width: 100vw;
  height: 100vh;
  overflow: hidden;
  background-color: #f8fafc;
}

/* 侧边栏 */
.sidebar {
  width: 260px;
  height: 100%;
  display: flex;
  flex-direction: column;
  background-color: #ffffff;
  border-right: 1px solid rgba(226, 232, 240, 0.9);
  transition: width 0.2s ease;
  user-select: none;
}

.brand-header {
  height: 64px;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 0 18px;
  border-bottom: 1px solid #f1f5f9;
  cursor: pointer;
}

.brand-logo {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  background: linear-gradient(135deg, #e0f2fe 0%, #bae6fd 100%);
  display: flex;
  align-items: center;
  justify-content: center;
}

.logo-flask {
  font-size: 20px;
}

.brand-info {
  display: flex;
  flex-direction: column;
}

.brand-title {
  font-size: 15px;
  font-weight: 700;
  color: #0f172a;
  letter-spacing: -0.01em;
}

.brand-subtitle {
  font-size: 11px;
  color: #94a3b8;
}

.menu-container {
  flex: 1;
  overflow-y: auto;
  padding: 8px 6px;
}

.sidebar-footer {
  padding: 12px 18px;
  border-top: 1px solid #f1f5f9;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.version-text {
  font-size: 12px;
}

/* 主内容区 */
.main-content {
  flex: 1;
  height: 100%;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.content-scrollable {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
}

/* 页面切换过渡动效 */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.15s ease, transform 0.15s ease;
}

.fade-enter-from {
  opacity: 0;
  transform: translateY(4px);
}

.fade-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}
</style>
