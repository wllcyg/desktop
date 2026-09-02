/**
 * PDF 模块公共类型定义与工具函数
 */

export interface MergeFileItem {
  id: string
  name: string
  path: string
  size: number
  totalPages: number
  pageRange: string
  title: string
  hasToc: boolean
  isLoadingInfo?: boolean
}

export interface SplitDocInfo {
  name: string
  path: string
  size: number
  totalPages: number
  hasToc: boolean
  toc: Array<{ level: number; title: string; page: number }>
}

export interface OrganizePageItem {
  id: string
  originalPageIndex: number // 0-based
  pageNumber: number // 1-based (原始页码)
  rotationDelta: number // 旋转累加 (0, 90, 180, 270)
  thumbnail: string
  width: number
  height: number
}

// 格式化文件大小
export function formatFileSize(bytes: number): string {
  if (!bytes || bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return (bytes / Math.pow(k, i)).toFixed(2) + ' ' + sizes[i]
}

// 健壮的 PDF 文件选择器（优先原生 IPC，未重启主进程时自动降级到 DOM 选择器）
export async function selectPdfFilesSafely(multiple = true): Promise<string[]> {
  try {
    // @ts-ignore
    const filePaths = await window.electron?.ipcRenderer?.invoke('dialog:select-pdf-files', multiple)
    if (Array.isArray(filePaths)) {
      return filePaths
    }
  } catch (err: any) {
    console.warn('IPC dialog:select-pdf-files 尚未就绪，自动降级为 DOM 文件选择器:', err.message)
  }

  return new Promise<string[]>((resolve) => {
    const input = document.createElement('input')
    input.type = 'file'
    input.accept = '.pdf,application/pdf'
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

// 健壮的保存文件路径获取器
export async function selectSavePathSafely(defaultName: string): Promise<string | null> {
  try {
    // @ts-ignore
    const filePath = await window.electron?.ipcRenderer?.invoke('dialog:save-file', {
      defaultPath: defaultName,
      filters: [{ name: 'PDF 文档', extensions: ['pdf'] }]
    })
    if (filePath) return filePath
  } catch (err: any) {
    console.warn('IPC dialog:save-file 尚未就绪，降级选择目录:', err.message)
    // 降级：选择输出目录并拼接文件名
    // @ts-ignore
    const dir = await window.electron?.ipcRenderer?.invoke('dialog:select-directory')
    if (dir) {
      return `${dir}\\${defaultName}`
    }
  }
  return null
}

// 打开文件
export async function openPath(targetPath: string) {
  if (!targetPath) return
  // @ts-ignore
  await window.electron?.ipcRenderer?.invoke('shell:open-path', targetPath)
}

// 打开文件所在文件夹
export async function showInFolder(targetPath: string) {
  if (!targetPath) return
  // @ts-ignore
  await window.electron?.ipcRenderer?.invoke('shell:show-item-in-folder', targetPath)
}
