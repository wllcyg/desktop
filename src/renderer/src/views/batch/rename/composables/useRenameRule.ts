/**
 * 批量重命名规则计算与冲突检测 Composable
 */
import { computed, Ref } from 'vue'
import {
  RenameFileItem,
  RenameMode,
  PatternRuleConfig,
  ReplaceRuleConfig,
  AffixRuleConfig
} from '../types'

export function useRenameRule(
  fileList: Ref<RenameFileItem[]>,
  currentMode: Ref<RenameMode>,
  patternConfig: PatternRuleConfig,
  replaceConfig: ReplaceRuleConfig,
  affixConfig: AffixRuleConfig
) {
  // 获取当前系统日期格式
  const getFormattedDate = (format: string): string => {
    const now = new Date()
    const y = String(now.getFullYear())
    const m = String(now.getMonth() + 1).padStart(2, '0')
    const d = String(now.getDate()).padStart(2, '0')
    if (format === 'YYYYMMDD') return `${y}${m}${d}`
    if (format === 'YYYY.MM.DD') return `${y}.${m}.${d}`
    return `${y}-${m}-${d}` // YYYY-MM-DD
  }

  // 格式化序号
  const formatNumber = (num: number, digits: number): string => {
    return String(num).padStart(digits, '0')
  }

  // 核心计算函数：根据规则为单个项生成新名称 (不含路径)
  const computeSingleNewName = (item: RenameFileItem, index: number): string => {
    let resultBaseName = item.baseName
    let resultExt = item.ext

    if (currentMode.value === 'pattern') {
      let tpl = patternConfig.template || '[原文件名]'
      const curNum = patternConfig.startNumber + index * patternConfig.step
      const numStr = formatNumber(curNum, patternConfig.digits)
      const dateStr = getFormattedDate(patternConfig.datePattern)

      tpl = tpl
        .replace(/\[原文件名\]/g, item.baseName)
        .replace(/\[序号\]/g, numStr)
        .replace(/\[序号2位\]/g, formatNumber(curNum, 2))
        .replace(/\[序号3位\]/g, formatNumber(curNum, 3))
        .replace(/\[序号4位\]/g, formatNumber(curNum, 4))
        .replace(/\[日期\]/g, dateStr)
        .replace(/\[创建日期\]/g, dateStr)

      resultBaseName = tpl
    } else if (currentMode.value === 'replace') {
      const find = replaceConfig.findText
      const replace = replaceConfig.replaceText || ''

      if (find) {
        try {
          if (replaceConfig.useRegex) {
            const flags = replaceConfig.caseSensitive ? 'g' : 'gi'
            const reg = new RegExp(find, flags)
            resultBaseName = resultBaseName.replace(reg, replace)
          } else {
            if (replaceConfig.caseSensitive) {
              resultBaseName = resultBaseName.replaceAll(find, replace)
            } else {
              // 忽略大小写替换
              const escaped = find.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
              const reg = new RegExp(escaped, 'gi')
              resultBaseName = resultBaseName.replace(reg, replace)
            }
          }
        } catch {
          // 正则语法错误时保持原样
        }
      }
    } else if (currentMode.value === 'affix') {
      // 裁剪前 N 个字符
      if (affixConfig.trimLeftCount > 0) {
        resultBaseName = resultBaseName.substring(affixConfig.trimLeftCount)
      }
      // 裁剪后 N 个字符
      if (affixConfig.trimRightCount > 0 && resultBaseName.length > affixConfig.trimRightCount) {
        resultBaseName = resultBaseName.substring(0, resultBaseName.length - affixConfig.trimRightCount)
      }

      // 附加前缀和后缀
      resultBaseName = `${affixConfig.prefix || ''}${resultBaseName}${affixConfig.suffix || ''}`

      // 扩展名处理
      if (affixConfig.extCase === 'lower') {
        resultExt = resultExt.toLowerCase()
      } else if (affixConfig.extCase === 'upper') {
        resultExt = resultExt.toUpperCase()
      }
    }

    // 组合最终文件名
    return `${resultBaseName}${resultExt}`
  }

  // 响应式计算全部文件的新名称与冲突检查
  const computedList = computed(() => {
    const list = fileList.value
    const nameMap = new Map<string, number>()

    // 第一遍：计算新名称
    const calculated = list.map((item, idx) => {
      const newFileName = computeSingleNewName(item, idx)
      const separator = item.dirPath.includes('/') ? '/' : '\\'
      const newFullPath = item.dirPath ? `${item.dirPath}${separator}${newFileName}` : newFileName
      const isChanged = newFileName !== item.originalName

      // 统计同名次数 (以同目录下完整路径为准)
      const lowerPath = newFullPath.toLowerCase()
      nameMap.set(lowerPath, (nameMap.get(lowerPath) || 0) + 1)

      return {
        ...item,
        newName: newFileName,
        newFullPath,
        isChanged
      }
    })

    // 第二遍：标记冲突项
    return calculated.map((item) => {
      const lowerPath = item.newFullPath.toLowerCase()
      const isConflict = (nameMap.get(lowerPath) || 0) > 1
      return {
        ...item,
        isConflict
      }
    })
  })

  // 是否存在同名冲突
  const hasConflict = computed(() => {
    return computedList.value.some((item) => item.isConflict)
  })

  // 变动文件数量
  const changedCount = computed(() => {
    return computedList.value.filter((item) => item.isChanged).length
  })

  return {
    computedList,
    hasConflict,
    changedCount
  }
}
