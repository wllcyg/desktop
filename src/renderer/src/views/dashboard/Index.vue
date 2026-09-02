<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()

const mvpTools = [
  {
    title: '图片工作台',
    desc: 'PixiJS GPU加速编辑、预设滤镜、文字水印与AI智能去水印',
    route: '/image-doc/studio',
    tag: 'MVP ⭐⭐⭐',
    color: '#0284c7'
  },
  {
    title: '图片去水印',
    desc: '批量清除下载课件、习题图片上的水印',
    route: '/image-doc/watermark',
    tag: 'MVP ⭐⭐⭐',
    color: '#059669'
  },
  {
    title: 'OCR 识别 / 公式提取',
    desc: '拍照试卷、化学方程式识别为文字或 LaTeX',
    route: '/image-doc/ocr',
    tag: 'MVP ⭐⭐⭐',
    color: '#7c3aed'
  },
  {
    title: '文件批量重命名',
    desc: '按班级/学号/考试名称规则批量规整试卷照片',
    route: '/batch/rename',
    tag: 'MVP ⭐⭐⭐',
    color: '#d97706'
  }
]

const categories = [
  {
    name: '一、图片/文档处理类',
    items: [
      { name: '图片工作台', route: '/image-doc/studio' },
      { name: '图片去水印', route: '/image-doc/watermark' },
      { name: 'OCR文字/公式识别', route: '/image-doc/ocr' },
      { name: 'PDF合并/拆分', route: '/image-doc/pdf-tool' }
    ]
  },
  {
    name: '二、批量处理类',
    items: [
      { name: '文件批量重命名', route: '/batch/rename' }
    ]
  }
]

const go = (path: string) => {
  router.push(path)
}
</script>

<template>
  <div class="dashboard-container">
    <!-- 欢迎 Banner -->
    <div class="welcome-banner">
      <div class="banner-content">
        <h1 class="banner-title">工具箱</h1>
        <p class="banner-subtitle">
          一站式高效桌面小工具集合：图片/文档处理、批量办公、数据统计与学科工具
        </p>
      </div>
      <div class="banner-tag">
        <n-tag type="success" round>高效 · 简洁 · 开箱即用</n-tag>
      </div>
    </div>

    <!-- MVP 重点功能快捷卡片 -->
    <div class="section-title">第一期 MVP 核心功能</div>
    <div class="mvp-grid">
      <div
        v-for="tool in mvpTools"
        :key="tool.route"
        class="mvp-card"
        @click="go(tool.route)"
      >
        <div class="mvp-card-header">
          <span class="mvp-title">{{ tool.title }}</span>
          <n-tag size="small" round :bordered="false" type="primary">
            {{ tool.tag }}
          </n-tag>
        </div>
        <p class="mvp-desc">{{ tool.desc }}</p>
        <div class="mvp-action">
          <span>进入工具</span>
          <span class="arrow">→</span>
        </div>
      </div>
    </div>

    <!-- 全功能矩阵速览 -->
    <div class="section-title">全部功能模块概览</div>
    <div class="categories-grid">
      <n-card
        v-for="cat in categories"
        :key="cat.name"
        :title="cat.name"
        size="small"
        class="cat-card"
        :bordered="false"
      >
        <div class="chips-list">
          <n-button
            v-for="item in cat.items"
            :key="item.route"
            size="small"
            secondary
            class="chip-btn"
            @click="go(item.route)"
          >
            {{ item.name }}
          </n-button>
        </div>
      </n-card>
    </div>
  </div>
</template>

<style scoped>
.dashboard-container {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.welcome-banner {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 24px 30px;
  background: linear-gradient(135deg, #0ea5e9 0%, #0284c7 50%, #0369a1 100%);
  border-radius: 16px;
  color: #ffffff;
  box-shadow: 0 10px 25px -5px rgba(14, 165, 233, 0.3);
}

.banner-title {
  margin: 0 0 6px 0;
  font-size: 24px;
  font-weight: 700;
  letter-spacing: -0.02em;
}

.banner-subtitle {
  margin: 0;
  font-size: 14px;
  opacity: 0.92;
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  color: #1e293b;
  margin-top: 4px;
}

.mvp-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 16px;
}

.mvp-card {
  display: flex;
  flex-direction: column;
  padding: 18px 20px;
  background: #ffffff;
  border-radius: 14px;
  border: 1px solid rgba(226, 232, 240, 0.9);
  cursor: pointer;
  transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
  box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.02);
}

.mvp-card:hover {
  transform: translateY(-2px);
  border-color: #38bdf8;
  box-shadow: 0 8px 20px -4px rgba(14, 165, 233, 0.15);
}

.mvp-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.mvp-title {
  font-size: 16px;
  font-weight: 600;
  color: #0f172a;
}

.mvp-desc {
  margin: 0 0 16px 0;
  font-size: 13px;
  color: #64748b;
  line-height: 1.5;
  flex: 1;
}

.mvp-action {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 13px;
  font-weight: 500;
  color: #0284c7;
}

.mvp-action .arrow {
  transition: transform 0.2s;
}

.mvp-card:hover .mvp-action .arrow {
  transform: translateX(4px);
}

.categories-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
  gap: 16px;
}

.cat-card {
  border-radius: 12px;
  background: #ffffff;
  border: 1px solid rgba(226, 232, 240, 0.8);
}

.chips-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.chip-btn {
  border-radius: 8px;
}
</style>
