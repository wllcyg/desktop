import { app, shell, BrowserWindow, ipcMain } from 'electron'
import { join } from 'path'
import { electronApp, optimizer, is } from '@electron-toolkit/utils'
import icon from '../../resources/icon.png?asset'
import { setupAutoUpdater } from './updater'
import { initPythonBridge } from './pythonBridge'
import { setupModelManagerIPC } from './modelManager'

function createWindow(): void {
  // Create the browser window.
  const mainWindow = new BrowserWindow({
    width: 1000,
    height: 720,
    show: false,
    autoHideMenuBar: true,
    title: '工具箱',
    icon,
    webPreferences: {
      preload: join(__dirname, '../preload/index.js'),
      sandbox: false
    }
  })

  mainWindow.on('ready-to-show', () => {
    mainWindow.show()
  })

  // 注册自动更新检测与状态广播
  setupAutoUpdater(mainWindow)

  mainWindow.webContents.setWindowOpenHandler((details) => {
    shell.openExternal(details.url)
    return { action: 'deny' }
  })

  // HMR for renderer base on electron-vite cli.
  // Load the remote URL for development or the local html file for production.
  if (is.dev && process.env['ELECTRON_RENDERER_URL']) {
    mainWindow.loadURL(process.env['ELECTRON_RENDERER_URL'])
  } else {
    mainWindow.loadFile(join(__dirname, '../renderer/index.html'))
  }
}

// This method will be called when Electron has finished
// initialization and is ready to create browser windows.
// Some APIs can only be used after this event occurs.
app.whenReady().then(async () => {
  // Set app user model id for windows
  electronApp.setAppUserModelId('com.app.toolbox')

  // Default open or close DevTools by F12 in development
  // and ignore CommandOrControl + R in production.
  // see https://github.com/alex8088/electron-toolkit/tree/master/packages/utils
  app.on('browser-window-created', (_, window) => {
    optimizer.watchWindowShortcuts(window)
  })

  // IPC test
  ipcMain.on('ping', () => console.log('pong'))

  // 注册原生文件/文件夹选择与批量保存 IPC
  ipcMain.handle('dialog:select-directory', async () => {
    const { dialog } = await import('electron')
    const result = await dialog.showOpenDialog({
      title: '选择导出保存目录',
      properties: ['openDirectory', 'createDirectory']
    })
    if (result.canceled || result.filePaths.length === 0) {
      return null
    }
    return result.filePaths[0]
  })

  ipcMain.handle('dialog:select-pdf-files', async (_, multiple = true) => {
    const { dialog } = await import('electron')
    const properties: Array<'openFile' | 'multiSelections'> = ['openFile']
    if (multiple) {
      properties.push('multiSelections')
    }
    const result = await dialog.showOpenDialog({
      title: '选择 PDF 文件',
      filters: [{ name: 'PDF 文档', extensions: ['pdf'] }],
      properties
    })
    if (result.canceled || result.filePaths.length === 0) {
      return []
    }
    return result.filePaths
  })

  ipcMain.handle('dialog:save-file', async (_, options: { defaultPath?: string; filters?: Array<{ name: string; extensions: string[] }> }) => {
    const { dialog } = await import('electron')
    const result = await dialog.showSaveDialog({
      title: '保存 PDF 文件',
      defaultPath: options.defaultPath || 'merged_document.pdf',
      filters: options.filters || [{ name: 'PDF 文档', extensions: ['pdf'] }]
    })
    if (result.canceled || !result.filePath) {
      return null
    }
    return result.filePath
  })

  ipcMain.handle('file:save-batch', async (_, { dirPath, items }: { dirPath: string; items: Array<{ name: string; base64: string }> }) => {
    const fs = await import('fs/promises')
    const path = await import('path')
    const savedPaths: string[] = []

    for (const item of items) {
      let b64 = item.base64
      if (b64.includes(',')) {
        b64 = b64.split(',')[1]
      }
      const buffer = Buffer.from(b64, 'base64')
      const targetPath = path.join(dirPath, item.name)
      await fs.writeFile(targetPath, buffer)
      savedPaths.push(targetPath)
    }
    return { success: true, count: savedPaths.length, dirPath }
  })

  ipcMain.handle('shell:open-path', async (_, targetPath: string) => {
    return await shell.openPath(targetPath)
  })

  ipcMain.handle('shell:show-item-in-folder', async (_, targetPath: string) => {
    shell.showItemInFolder(targetPath)
    return true
  })

  // 启动 Python 核心服务 (管道模式)
  initPythonBridge()

  // 注册 AI 模型管理中心 IPC
  setupModelManagerIPC()

  createWindow()

  app.on('activate', function () {
    // On macOS it's common to re-create a window in the app when the
    // dock icon is clicked and there are no other windows open.
    if (BrowserWindow.getAllWindows().length === 0) createWindow()
  })
})

// Quit when all windows are closed, except on macOS. There, it's common
// for applications and their menu bar to stay active until the user quits
// explicitly with Cmd + Q.
app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit()
  }
})

// In this file you can include the rest of your app's specific main process
// code. You can also put them in separate files and require them here.
