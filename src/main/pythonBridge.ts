/**
 * Python 核心服务进程管道通信 (JSON-RPC over stdin/stdout)
 *
 * 1. 零网络端口占用，零防火墙弹窗
 * 2. 进程常驻内存，模型加载一次，毫秒级响应
 * 3. 随 Electron 应用生命周期自动拉起和退出清理
 */

import { ChildProcess, spawn } from 'child_process'
import { app, ipcMain } from 'electron'
import { join } from 'path'
import { existsSync } from 'fs'
import { createInterface } from 'readline'
import { is } from '@electron-toolkit/utils'

let pyProcess: ChildProcess | null = null
let isReady = false
let requestId = 0

interface PendingPromise {
  resolve: (value: any) => void
  reject: (reason?: any) => void
  timer: NodeJS.Timeout
}

const pendingRequests = new Map<number, PendingPromise>()

/**
 * 获取 Python 执行路径
 */
function getPyServerCommand(): { command: string; args: string[]; cwd: string } {
  const rootDir = process.cwd()

  if (is.dev) {
    const venvPaths = [
      join(rootDir, 'py_server', '.venv', 'bin', 'python'),
      join(rootDir, 'py_server', '.venv', 'Scripts', 'python.exe'),
      join(rootDir, '.venv', 'bin', 'python'),
      join(rootDir, '.venv', 'Scripts', 'python.exe'),
      join(rootDir, 'venv', 'bin', 'python'),
      join(rootDir, 'venv', 'Scripts', 'python.exe')
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

    const scriptPath = join(process.resourcesPath, 'py_server', 'main.py')
    return { command: 'python', args: [scriptPath], cwd: join(process.resourcesPath, 'py_server') }
  }
}

let initPromise: Promise<boolean> | null = null

/**
 * 启动 Python 子进程并建立管道监听
 */
export function initPythonBridge(): Promise<boolean> {
  if (pyProcess && isReady) {
    return Promise.resolve(true)
  }
  if (initPromise) {
    return initPromise
  }

  initPromise = new Promise<boolean>((resolve) => {
    const { command, args, cwd } = getPyServerCommand()
    console.log(`[PythonBridge] Starting Python bridge: ${command} ${args.join(' ')} (cwd: ${cwd})`)

    try {
      pyProcess = spawn(command, args, {
        cwd,
        stdio: ['pipe', 'pipe', 'pipe'],
        env: {
          ...process.env,
          PYTHONIOENCODING: 'utf-8',
          PYTHONUNBUFFERED: '1',
          PYTHONUTF8: '1'
        }
      })

      // 使用 readline 按行解析 stdout 输出的 JSON-RPC 消息
      if (pyProcess.stdout) {
        const rl = createInterface({ input: pyProcess.stdout })
        rl.on('line', (line) => {
          line = line.trim()
          if (!line) return

          try {
            const data = JSON.parse(line)

            // 处理首次就绪事件
            if (data.event === 'ready') {
              console.log(`[PythonBridge] Python core service ready (v${data.version}) [OK]`)
              isReady = true
              resolve(true)
              return
            }

            // 处理 JSON-RPC 响应
            const reqId = data.id
            if (reqId !== undefined && pendingRequests.has(reqId)) {
              const pending = pendingRequests.get(reqId)!
              clearTimeout(pending.timer)
              pendingRequests.delete(reqId)

              if (data.error) {
                pending.reject(new Error(data.error.message || 'Python error'))
              } else {
                pending.resolve(data.result)
              }
            }
          } catch (e) {
            console.log(`[PythonBridge stdout] ${line}`)
          }
        })
      }

      pyProcess.stderr?.on('data', (data: Buffer) => {
        const errText = data.toString('utf-8').trim()
        console.error(`[PythonBridge stderr] ${errText}`)
      })

      pyProcess.on('error', (err) => {
        console.error('[PythonBridge] Process error:', err.message)
        isReady = false
        pyProcess = null
        resolve(false)
      })

      pyProcess.on('exit', (code) => {
        console.log(`[PythonBridge] Process exited, code=${code}`)
        isReady = false
        // 拒绝所有未决请求
        for (const pending of pendingRequests.values()) {
          clearTimeout(pending.timer)
          pending.reject(new Error('Python process exited'))
        }
        pendingRequests.clear()
        pyProcess = null
      })

      // 20 秒超时保护 (给初次冷启动导包预留充足时间)
      setTimeout(() => {
        if (!isReady) {
          console.warn('[PythonBridge] Timeout waiting for ready event')
          resolve(false)
        }
      }, 20000)
    } catch (err) {
      console.error('[PythonBridge] spawn error:', err)
      resolve(false)
    }
  }).finally(() => {
    initPromise = null
  })

  return initPromise
}

/**
 * 向 Python 服务发送 RPC 调用
 */
export async function callPython(
  method: string,
  params: Record<string, any> = {},
  timeoutMs = 60000
): Promise<any> {
  if (!pyProcess || !pyProcess.stdin || !isReady) {
    const ready = await initPythonBridge()
    if (!ready || !pyProcess || !pyProcess.stdin || !isReady) {
      throw new Error('Python 核心服务未就绪，请确保已安装 Python 依赖')
    }
  }

  return new Promise((resolve, reject) => {
    const currentId = ++requestId
    const payload = JSON.stringify({
      jsonrpc: '2.0',
      id: currentId,
      method,
      params
    })

    const timer = setTimeout(() => {
      if (pendingRequests.has(currentId)) {
        pendingRequests.delete(currentId)
        reject(new Error(`Python method [${method}] execution timeout (${timeoutMs / 1000}s)`))
      }
    }, timeoutMs)

    pendingRequests.set(currentId, { resolve, reject, timer })

    try {
      if (!pyProcess?.stdin) {
        throw new Error('Python 进程输入管道未准备好')
      }
      pyProcess.stdin.write(payload + '\n', 'utf-8')
    } catch (err) {
      clearTimeout(timer)
      pendingRequests.delete(currentId)
      reject(err)
    }
  })
}

/**
 * 停止 Python 进程
 */
export function stopPythonBridge(): void {
  if (pyProcess) {
    console.log('[PythonBridge] Closing Python process...')
    pyProcess.kill('SIGTERM')
    setTimeout(() => {
      if (pyProcess && !pyProcess.killed) {
        pyProcess.kill('SIGKILL')
      }
      pyProcess = null
    }, 2000)
  }
}

// 注册 IPC 处理程序供渲染进程调用
ipcMain.handle('py:call', async (_, { method, params }) => {
  return await callPython(method, params)
})

ipcMain.handle('py:is-ready', () => isReady)

app.on('will-quit', () => {
  stopPythonBridge()
})
