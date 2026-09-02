/**
 * 批量重命名模块类型定义与辅助工具
 */

export interface RenameFileItem {
  id: string
  originalName: string // 原文件名 (含扩展名)
  baseName: string // 原文件名 (不含扩展名)
  ext: string // 扩展名 (如 .jpg)
  dirPath: string // 所在目录
  fullPath: string // 完整原始绝对路径
  newName: string // 经规则计算后的新文件名 (含扩展名)
  newFullPath: string // 完整新绝对路径
  status: 'pending' | 'success' | 'locked' | 'error'
  errorMsg?: string
  isConflict?: boolean // 是否同名冲突
  isChanged?: boolean // 名称是否发生改变
}

export type RenameMode = 'pattern' | 'replace' | 'affix'

export interface PatternRuleConfig {
  template: string // 例如: "初三1班_[序号3位]_[原文件名]"
  startNumber: number
  step: number
  digits: number // 补零位数 (如 2 -> 01, 3 -> 001)
  datePattern: string // YYYY-MM-DD
}

export interface ReplaceRuleConfig {
  findText: string
  replaceText: string
  useRegex: boolean
  caseSensitive: boolean
}

export interface AffixRuleConfig {
  prefix: string
  suffix: string
  trimLeftCount: number
  trimRightCount: number
  extCase: 'keep' | 'lower' | 'upper'
}

export interface RollbackRecord {
  old_path: string
  new_path: string
}

// 通用安全文件选择器（优先 IPC，带 HTML5 降级）
export async function selectAnyFilesSafely(multiple = true): Promise<string[]> {
  try {
    // @ts-ignore
    const filePaths = await window.electron?.ipcRenderer?.invoke('dialog:select-any-files', multiple)
    if (Array.isArray(filePaths)) {
      return filePaths
    }
  } catch (err: any) {
    console.warn('IPC dialog:select-any-files 尚未就绪，自动降级为 DOM 文件选择器:', err.message)
  }

  return new Promise<string[]>((resolve) => {
    const input = document.createElement('input')
    input.type = 'file'
    input.multiple = multiple
    input.style.display = 'none'

    input.onchange = () => {
      const files = input.files ? Array.from(input.files) : []
      const paths = files
        .map((f: any) => f.path)
        .filter((p: string | undefined): p is string => Boolean(p))
      if (input.parentNode) {
        document.body.removeChild(input)
      }
      resolve(paths)
    }

    input.oncancel = () => {
      if (input.parentNode) {
        document.body.removeChild(input)
      }
      resolve([])
    }

    document.body.appendChild(input)
    input.click()
  })
}

// 分离文件名与扩展名
export function parseFilePath(fullPath: string): { dirPath: string; originalName: string; baseName: string; ext: string } {
  const normalized = fullPath.replace(/\\/g, '/')
  const lastSlash = normalized.lastIndexOf('/')
  const dirPath = lastSlash >= 0 ? fullPath.substring(0, lastSlash) : ''
  const originalName = lastSlash >= 0 ? fullPath.substring(lastSlash + 1) : fullPath

  const lastDot = originalName.lastIndexOf('.')
  if (lastDot > 0) {
    return {
      dirPath,
      originalName,
      baseName: originalName.substring(0, lastDot),
      ext: originalName.substring(lastDot)
    }
  } else {
    return {
      dirPath,
      originalName,
      baseName: originalName,
      ext: ''
    }
  }
}
