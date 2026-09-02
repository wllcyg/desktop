import { BrowserWindow, ipcMain, app } from 'electron'
import { autoUpdater } from 'electron-updater'
import { is } from '@electron-toolkit/utils'
import { join } from 'path'

export function setupAutoUpdater(mainWindow: BrowserWindow): void {
  // 开发环境下配置测试更新路径
  if (is.dev) {
    autoUpdater.updateConfigPath = join(__dirname, '../../dev-app-update.yml')
    // 开发环境下允许预发布版本检测
    autoUpdater.allowPrerelease = true
  }

  // 默认不自动下载，发现新版本后可由用户确认或按策略下载
  autoUpdater.autoDownload = true
  autoUpdater.autoInstallOnAppQuit = true

  // 状态事件向渲染进程广播
  const sendStatusToWindow = (channel: string, text: string, data?: unknown): void => {
    if (!mainWindow.isDestroyed()) {
      mainWindow.webContents.send('updater:message', { channel, text, data })
    }
  }

  // 监听更新生命周期
  autoUpdater.on('checking-for-update', () => {
    sendStatusToWindow('checking', '正在检查更新...')
  })

  autoUpdater.on('update-available', (info) => {
    sendStatusToWindow('available', `发现新版本 v${info.version}`, info)
  })

  autoUpdater.on('update-not-available', (info) => {
    sendStatusToWindow('not-available', '当前已是最新版本', info)
  })

  autoUpdater.on('error', (err) => {
    sendStatusToWindow('error', `更新检查异常: ${err == null ? '未知错误' : err.message}`)
  })

  autoUpdater.on('download-progress', (progressObj) => {
    sendStatusToWindow('download-progress', `正在下载更新: ${Math.floor(progressObj.percent)}%`, progressObj)
  })

  autoUpdater.on('update-downloaded', (info) => {
    sendStatusToWindow('downloaded', `新版本 v${info.version} 已下载完成，重启后生效`, info)
  })

  // IPC: 手动检查更新
  ipcMain.handle('updater:check', async () => {
    try {
      const result = await autoUpdater.checkForUpdates()
      return { success: true, result }
    } catch (error: any) {
      return { success: false, message: error?.message || '检查更新失败' }
    }
  })

  // IPC: 退出并安装
  ipcMain.handle('updater:quit-and-install', () => {
    autoUpdater.quitAndInstall()
  })

  // 应用启动 3 秒后在后台静默检查一次更新（避免阻塞首屏渲染）
  app.whenReady().then(() => {
    setTimeout(() => {
      autoUpdater.checkForUpdatesAndNotify().catch((err) => {
        console.warn('Auto update check failed:', err)
      })
    }, 3000)
  })
}
