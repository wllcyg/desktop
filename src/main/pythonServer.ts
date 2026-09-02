/**
 * Python 核心服务生命周期管理
 *
 * 在 Electron 主进程中管理 Python HTTP 微服务的启动、健康检查与退出清理。
 * Python 服务绑定在 127.0.0.1:18520 本地回环端口。
 */

import { ChildProcess, spawn } from 'child_process'
import { app } from 'electron'
import { join } from 'path'
import { existsSync } from 'fs'
import http from 'http'
import { is } from '@electron-toolkit/utils'

let pyProcess: ChildProcess | null = null

const PY_HOST = '127.0.0.1'
const PY_PORT = 18520

/**
 * 获取 Python 服务的启动路径
 * 开发环境：直接用系统 python 执行 py_server/main.py
 * 生产环境：执行打包好的 resources/py_server/server.exe（PyInstaller 产物）
 */
function getPyServerCommand(): { command: string; args: string[]; cwd: string } {
  const rootDir = process.cwd()

  if (is.dev) {
    // 优先检测本地虚拟环境 Python 解释器
    const venvPaths = [
      join(rootDir, '.venv', 'Scripts', 'python.exe'),
      join(rootDir, 'venv', 'Scripts', 'python.exe'),
      join(rootDir, 'py_server', '.venv', 'Scripts', 'python.exe'),
      join(rootDir, '.venv', 'bin', 'python'),
      join(rootDir, 'venv', 'bin', 'python')
    ]

    let pyExec = 'python'
    for (const p of venvPaths) {
      if (existsSync(p)) {
        pyExec = p
        break
      }
    }

    const scriptPath = join(rootDir, 'py_server', 'main.py')
    return { command: pyExec, args: [scriptPath], cwd: join(rootDir, 'py_server') }
  } else {
    // 生产环境：检查 PyInstaller 打包产物
    const possibleExes = [
      join(process.resourcesPath, 'py_server', 'server', 'server.exe'),
      join(process.resourcesPath, 'py_server', 'server.exe'),
      join(process.resourcesPath, 'py_server', 'server', 'server'),
      join(process.resourcesPath, 'py_server', 'server')
    ]

    for (const exe of possibleExes) {
      if (existsSync(exe)) {
        return { command: exe, args: [], cwd: join(process.resourcesPath, 'py_server') }
      }
    }

    // 降级方案
    const scriptPath = join(process.resourcesPath, 'py_server', 'main.py')
    return { command: 'python', args: [scriptPath], cwd: join(process.resourcesPath, 'py_server') }
  }
}

/**
 * 启动 Python 服务子进程
 */
export function startPythonServer(): void {
  if (pyProcess) {
    console.log('[PythonServer] 服务已在运行中')
    return
  }

  const { command, args, cwd } = getPyServerCommand()
  console.log(`[PythonServer] 正在启动: ${command} ${args.join(' ')} (cwd: ${cwd})`)

  try {
    pyProcess = spawn(command, args, {
      cwd,
      stdio: ['pipe', 'pipe', 'pipe'],
      env: { ...process.env }
    })

    pyProcess.stdout?.on('data', (data: Buffer) => {
      console.log(`[PythonServer] ${data.toString().trim()}`)
    })

    pyProcess.stderr?.on('data', (data: Buffer) => {
      console.error(`[PythonServer] ${data.toString().trim()}`)
    })

    pyProcess.on('error', (err) => {
      console.error('[PythonServer] 启动失败:', err.message)
      pyProcess = null
    })

    pyProcess.on('exit', (code) => {
      console.log(`[PythonServer] 进程退出, code=${code}`)
      pyProcess = null
    })
  } catch (err) {
    console.error('[PythonServer] spawn 异常:', err)
    pyProcess = null
  }
}

/**
 * 健康检查：探测 Python 服务是否已就绪
 * 最多重试 maxRetries 次，每次间隔 intervalMs 毫秒
 */
export function waitForPythonServer(
  maxRetries = 30,
  intervalMs = 1000
): Promise<boolean> {
  return new Promise((resolve) => {
    let retries = 0

    const check = (): void => {
      const req = http.get(`http://${PY_HOST}:${PY_PORT}/api/health`, (res) => {
        if (res.statusCode === 200) {
          console.log('[PythonServer] 服务就绪 ✓')
          resolve(true)
        } else {
          retry()
        }
      })

      req.on('error', () => {
        retry()
      })

      req.setTimeout(2000, () => {
        req.destroy()
        retry()
      })
    }

    const retry = (): void => {
      retries++
      if (retries >= maxRetries) {
        console.error(`[PythonServer] 等待超时 (${maxRetries} 次重试后放弃)`)
        resolve(false)
      } else {
        setTimeout(check, intervalMs)
      }
    }

    check()
  })
}

/**
 * 停止 Python 服务子进程
 */
export function stopPythonServer(): void {
  if (pyProcess) {
    console.log('[PythonServer] 正在关闭...')
    pyProcess.kill('SIGTERM')

    // 给 2 秒优雅退出，超时强制 kill
    setTimeout(() => {
      if (pyProcess && !pyProcess.killed) {
        pyProcess.kill('SIGKILL')
      }
      pyProcess = null
    }, 2000)
  }
}

/**
 * 获取 Python 服务基础 URL
 */
export function getPyServerBaseUrl(): string {
  return `http://${PY_HOST}:${PY_PORT}`
}

// 应用退出时自动清理 Python 子进程
app.on('will-quit', () => {
  stopPythonServer()
})
