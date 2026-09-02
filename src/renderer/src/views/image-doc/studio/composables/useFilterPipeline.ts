/**
 * PixiJS GPU 滤镜流水线与着色器矩阵组合器
 */

import { ColorMatrixFilter, Filter } from 'pixi.js'
import { ImageRecipe } from '../types'

export function useFilterPipeline() {
  /**
   * 根据配方生成 PixiJS 滤镜数组
   */
  const buildFilterList = (recipe: ImageRecipe): Filter[] => {
    const filters: Filter[] = []
    const colorFilter = new ColorMatrixFilter()

    // 1. 预设滤镜基础矩阵映射
    switch (recipe.filterPreset) {
      case 'scanner_whiten':
        // 扫描仪白底化：提高白阶亮度与高对比度，让发灰的试卷背景纯白
        colorFilter.brightness(1.25, false)
        colorFilter.contrast(1.65, true)
        break

      case 'pure_bw':
        // 纯净黑白二值化
        colorFilter.blackAndWhite(false)
        colorFilter.contrast(2.2, true)
        break

      case 'ink_boost':
        // 蓝黑笔墨增强：提升对比度与微调冷色调
        colorFilter.contrast(1.3, false)
        colorFilter.saturate(0.3, true)
        break

      case 'doc_contrast':
        // 昏暗文档高光对比
        colorFilter.brightness(1.2, false)
        colorFilter.contrast(1.4, true)
        break

      case 'vintage':
        // 复古胶片：褐色调与低饱和
        colorFilter.sepia(false)
        colorFilter.brightness(1.05, true)
        colorFilter.contrast(1.1, true)
        break

      case 'warm_sunlight':
        // 暖阳金黄
        colorFilter.tint(0xfff0d0, false)
        colorFilter.brightness(1.08, true)
        break

      case 'cool_nordic':
        // 清冷北欧青蓝
        colorFilter.tint(0xd0e8ff, false)
        colorFilter.contrast(1.15, true)
        break

      case 'cinematic':
        // 电影青橙质感
        colorFilter.contrast(1.25, false)
        colorFilter.saturate(0.2, true)
        break

      case 'polaroid':
        // 拍立得复古
        colorFilter.polaroid(false)
        break

      case 'classic_mono':
        // 经典黑白影调
        colorFilter.blackAndWhite(false)
        colorFilter.contrast(1.35, true)
        break

      case 'none':
      default:
        colorFilter.reset()
        break
    }

    // 2. 浅灰背景平铺水印实时 GPU 增强预览
    if (recipe.watermarkClean?.cleanFaintWatermark) {
      // 保持适度对比度，防止文字笔画断裂
      colorFilter.contrast(1.25, false)
    }

    // 3. 红色印章 / 批改痕迹滤除预览
    if (recipe.watermarkClean?.cleanRedStamp) {
      colorFilter.saturate(-0.3, true)
    }

    // 3. 叠加参数微调 (曝光/亮度/对比度/饱和度/色温/色相)
    if (recipe.exposure !== 0) {
      colorFilter.brightness(1 + recipe.exposure / 100, true)
    }

    if (recipe.brightness !== 0) {
      colorFilter.brightness(1 + recipe.brightness / 100, true)
    }

    if (recipe.contrast !== 0) {
      colorFilter.contrast(1 + recipe.contrast / 100, true)
    }

    if (recipe.saturation !== 0) {
      if (recipe.saturation < 0) {
        colorFilter.desaturate()
      } else {
        colorFilter.saturate(recipe.saturation / 100, true)
      }
    }

    if (recipe.temperature !== 0) {
      if (recipe.temperature > 0) {
        // 暖色偏黄红
        colorFilter.tint(0xfff5e6, true)
      } else {
        // 冷色偏青蓝
        colorFilter.tint(0xe6f5ff, true)
      }
    }

    if (recipe.hue !== 0) {
      colorFilter.hue(recipe.hue, true)
    }

    filters.push(colorFilter)

    return filters
  }

  return { buildFilterList }
}
