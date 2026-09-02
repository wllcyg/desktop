import { createRouter, createWebHashHistory, RouteRecordRaw } from 'vue-router'
import MainLayout from '@renderer/layouts/MainLayout.vue'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    component: MainLayout,
    children: [
      {
        path: '',
        name: 'Dashboard',
        component: () => import('@renderer/views/dashboard/Index.vue'),
        meta: { title: '工作台首页', icon: 'home' }
      },
      // 一、图片与文档处理
      {
        path: 'image-doc/watermark',
        name: 'Watermark',
        component: () => import('@renderer/views/image-doc/WatermarkView.vue'),
        meta: { title: '图片去水印', isMvp: true }
      },
      {
        path: 'image-doc/ocr',
        name: 'Ocr',
        component: () => import('@renderer/views/image-doc/OcrView.vue'),
        meta: { title: '文字/公式OCR', isMvp: true }
      },
      {
        path: 'image-doc/pdf-convert',
        name: 'PdfConvert',
        component: () => import('@renderer/views/image-doc/PdfConvertView.vue'),
        meta: { title: 'PDF转Word', isMvp: true }
      },
      {
        path: 'image-doc/pdf-tool',
        name: 'PdfTool',
        component: () => import('@renderer/views/image-doc/PdfToolView.vue'),
        meta: { title: 'PDF合并/拆分' }
      },
      {
        path: 'image-doc/scan-enhance',
        name: 'ScanEnhance',
        component: () => import('@renderer/views/image-doc/ScanEnhanceView.vue'),
        meta: { title: '扫描件校正' }
      },
      {
        path: 'image-doc/studio',
        name: 'ImageStudio',
        component: () => import('@renderer/views/image-doc/ImageStudioView.vue'),
        meta: { title: '图片工作台' }
      },
      // 二、批量/重复劳动类
      {
        path: 'batch/rename',
        name: 'Rename',
        component: () => import('@renderer/views/batch/RenameView.vue'),
        meta: { title: '文件批量重命名', isMvp: true }
      },
      {
        path: 'batch/classify',
        name: 'Classify',
        component: () => import('@renderer/views/batch/ClassifyView.vue'),
        meta: { title: '文件自动归类' }
      },
      {
        path: 'batch/template-fill',
        name: 'TemplateFill',
        component: () => import('@renderer/views/batch/TemplateFillView.vue'),
        meta: { title: '模板批量填充' }
      },
      // 三、成绩与数据统计类
      {
        path: 'grade/stat',
        name: 'GradeStat',
        component: () => import('@renderer/views/grade/StatView.vue'),
        meta: { title: '成绩单自动统计' }
      },
      {
        path: 'grade/chart',
        name: 'GradeChart',
        component: () => import('@renderer/views/grade/ChartView.vue'),
        meta: { title: '成绩趋势图表' }
      },
      {
        path: 'grade/accuracy',
        name: 'GradeAccuracy',
        component: () => import('@renderer/views/grade/AccuracyView.vue'),
        meta: { title: '试题正确率分析' }
      },
      // 四、化学学科专用小工具
      {
        path: 'chemistry/balancer',
        name: 'Balancer',
        component: () => import('@renderer/views/chemistry/BalancerView.vue'),
        meta: { title: '化学方程式配平' }
      },
      {
        path: 'chemistry/periodic-table',
        name: 'PeriodicTable',
        component: () => import('@renderer/views/chemistry/PeriodicTableView.vue'),
        meta: { title: '元素周期表速查' }
      },
      {
        path: 'chemistry/molecule',
        name: 'Molecule',
        component: () => import('@renderer/views/chemistry/MoleculeView.vue'),
        meta: { title: '分子结构图库' }
      },
      {
        path: 'chemistry/lab-safety',
        name: 'LabSafety',
        component: () => import('@renderer/views/chemistry/LabSafetyView.vue'),
        meta: { title: '实验安全/步骤清单' }
      },
      // 五、课件生成与设置
      {
        path: 'courseware',
        name: 'Courseware',
        component: () => import('@renderer/views/courseware/CoursewareView.vue'),
        meta: { title: '课件PPT生成' }
      },
      {
        path: 'settings',
        name: 'Settings',
        component: () => import('@renderer/views/settings/SettingsView.vue'),
        meta: { title: '系统设置' }
      },
      {
        path: 'settings/models',
        name: 'ModelManager',
        component: () => import('@renderer/views/settings/ModelManagerView.vue'),
        meta: { title: 'AI模型管理' }
      }
    ]
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/'
  }
]

const router = createRouter({
  history: createWebHashHistory(),
  routes
})

export default router
