'use strict'

const { app, BrowserWindow, dialog, ipcMain, net, protocol, shell } = require('electron')
const fs = require('fs')
const path = require('path')
const { pathToFileURL } = require('url')
const { spawn, spawnSync } = require('child_process')

const isDev = process.env.NODE_ENV === 'development' || !app.isPackaged

const BACKEND_PORT = 8000
const BACKEND_HEALTH_URL = `http://127.0.0.1:${BACKEND_PORT}/api/health`
const BACKEND_STARTUP_TIMEOUT_MS = 30_000
const BACKEND_STOP_TIMEOUT_MS = 5_000

// The packaged renderer is served from app://bundle/ rather than file:// so it
// has a real origin ("app://bundle") that the backend's CORS policy can allow.
// file:// pages send `Origin: null`, which can't be safely allow-listed.
const APP_SCHEME = 'app'
const APP_HOST = 'bundle'
const DIST_DIR = path.join(__dirname, '../dist')

protocol.registerSchemesAsPrivileged([
  { scheme: APP_SCHEME, privileges: { standard: true, secure: true, supportFetchAPI: true } },
])

app.setName('DeltaAdvisor')
// Keep the original data folder so existing .env and chat history survive the rename.
app.setPath('userData', path.join(app.getPath('appData'), 'ibkr-financial-advisor'))

const ENV_TEMPLATE = `# DeltaAdvisor configuration
ANTHROPIC_API_KEY=
IBKR_PAPER_PORT=7497
IBKR_LIVE_PORT=7496
IBKR_CLIENT_ID=1
`

let mainWindow = null
let backendProcess = null
let isQuitting = false

function registerAppProtocol() {
  protocol.handle(APP_SCHEME, (request) => {
    const { host, pathname } = new URL(request.url)
    const filePath = path.normalize(path.join(DIST_DIR, decodeURIComponent(pathname)))
    if (host !== APP_HOST || !filePath.startsWith(DIST_DIR + path.sep)) {
      return new Response('Not found', { status: 404 })
    }
    return net.fetch(pathToFileURL(filePath).toString())
  })
}

// The backend reads `.env` and writes its SQLite DB relative to its working
// directory, so run it from the per-user data dir (~/Library/Application Support/<app>).
function prepareDataDir() {
  const dataDir = app.getPath('userData')
  fs.mkdirSync(dataDir, { recursive: true })
  const envPath = path.join(dataDir, '.env')
  if (!fs.existsSync(envPath)) fs.writeFileSync(envPath, ENV_TEMPLATE)
  return dataDir
}

// PyInstaller --onefile runs as a bootloader plus a child Python process, so the
// backend is spawned as its own process group and signalled as a group.
function signalBackend(pid, signal) {
  try {
    process.kill(process.platform === 'win32' ? pid : -pid, signal)
  } catch {
    // already gone
  }
}

function backendPidFile() {
  return path.join(app.getPath('userData'), 'backend.pid')
}

// A previous run that crashed or was force-quit can leave its backend holding the port.
function killStaleBackend(backendPath) {
  if (process.platform === 'win32') return
  let pid
  try {
    pid = Number(fs.readFileSync(backendPidFile(), 'utf8'))
  } catch {
    return
  }
  fs.rmSync(backendPidFile(), { force: true })
  if (!pid) return
  // Guard against PID reuse: only kill it if that PID is still our backend binary.
  const { stdout } = spawnSync('ps', ['-o', 'command=', '-p', String(pid)], { encoding: 'utf8' })
  if (stdout && stdout.includes(backendPath)) signalBackend(pid, 'SIGKILL')
}

function startBackend() {
  if (isDev) {
    // In dev mode the backend is started by `npm run dev:backend`
    // Electron just connects to it — no need to spawn here.
    return
  }

  // Production: launch the frozen PyInstaller binary bundled as an extra resource
  const binaryName = process.platform === 'win32' ? 'server.exe' : 'server'
  const backendPath = path.join(process.resourcesPath, 'backend', binaryName)

  const dataDir = prepareDataDir()
  killStaleBackend(backendPath)

  backendProcess = spawn(backendPath, [], {
    cwd: dataDir,
    env: { ...process.env, BACKEND_PORT: String(BACKEND_PORT) },
    detached: process.platform !== 'win32', // own process group, see signalBackend
  })
  if (backendProcess.pid) fs.writeFileSync(backendPidFile(), String(backendProcess.pid))

  backendProcess.stdout.on('data', (d) => console.log('[backend]', d.toString()))
  backendProcess.stderr.on('data', (d) => console.error('[backend]', d.toString()))
  backendProcess.on('error', (err) => console.error('[backend] failed to start:', err))
  backendProcess.on('exit', (code, signal) => {
    backendProcess = null
    if (!isQuitting) {
      dialog.showErrorBox(
        'Backend stopped',
        `The DeltaAdvisor backend exited unexpectedly (code ${code}, signal ${signal}).`,
      )
    }
  })
}

// Ask the backend to shut down, and force-kill it if it hasn't exited in time.
function stopBackend() {
  const proc = backendProcess
  backendProcess = null
  if (!proc || !proc.pid) return Promise.resolve()
  return new Promise((resolve) => {
    const timer = setTimeout(() => signalBackend(proc.pid, 'SIGKILL'), BACKEND_STOP_TIMEOUT_MS)
    proc.once('exit', () => {
      clearTimeout(timer)
      fs.rmSync(backendPidFile(), { force: true })
      resolve()
    })
    signalBackend(proc.pid, 'SIGTERM')
  })
}

async function waitForBackend() {
  const deadline = Date.now() + BACKEND_STARTUP_TIMEOUT_MS
  while (Date.now() < deadline) {
    if (!isDev && !backendProcess) return false // exited during startup
    try {
      const res = await net.fetch(BACKEND_HEALTH_URL)
      if (res.ok) return true
    } catch {
      // not listening yet
    }
    await new Promise((resolve) => setTimeout(resolve, 250))
  }
  return false
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1440,
    height: 900,
    minWidth: 1024,
    minHeight: 680,
    titleBarStyle: 'hiddenInset',
    backgroundColor: '#0a0a0a',
    webPreferences: {
      preload: path.join(__dirname, 'preload.cjs'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: false,
    },
  })

  if (isDev) {
    mainWindow.loadURL('http://localhost:5273')
    mainWindow.webContents.openDevTools()
  } else {
    mainWindow.loadURL(`${APP_SCHEME}://${APP_HOST}/index.html`)
  }

  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url)
    return { action: 'deny' }
  })
}

app.whenReady().then(async () => {
  // Packaged builds get the icon from the .icns in the bundle; in dev the dock would show Electron's.
  if (isDev && process.platform === 'darwin') app.dock.setIcon(path.join(__dirname, '../assets/icon.png'))
  registerAppProtocol()
  startBackend()

  if (!isDev && !(await waitForBackend())) {
    // Quit while starting up: before-quit is already stopping the backend.
    if (isQuitting) return
    dialog.showErrorBox(
      'Backend failed to start',
      `The DeltaAdvisor backend did not become ready on port ${BACKEND_PORT}.`,
    )
    app.quit()
    return
  }

  createWindow()

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow()
  })
})

app.on('window-all-closed', () => {
  // On macOS the app stays alive in the dock, so keep the backend running too;
  // it's stopped in before-quit.
  if (process.platform !== 'darwin') app.quit()
})

app.on('before-quit', (event) => {
  isQuitting = true
  if (!backendProcess) return
  // Hold the quit until the backend has exited, so it can't outlive the app.
  event.preventDefault()
  stopBackend().then(() => app.quit())
})

// IPC handlers
ipcMain.handle('get-app-version', () => app.getVersion())
ipcMain.handle('open-external', (_event, url) => shell.openExternal(url))
