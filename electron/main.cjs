'use strict'

const { app, BrowserWindow, ipcMain, shell } = require('electron')
const path = require('path')
const { spawn } = require('child_process')

const isDev = process.env.NODE_ENV === 'development' || !app.isPackaged

let mainWindow = null
let backendProcess = null

function startBackend() {
  if (isDev) {
    // In dev mode the backend is started by `npm run dev:backend`
    // Electron just connects to it — no need to spawn here.
    return
  }

  // Production: launch the frozen PyInstaller binary bundled as an extra resource
  const binaryName = process.platform === 'win32' ? 'server.exe' : 'server'
  const backendPath = path.join(process.resourcesPath, 'backend', binaryName)

  backendProcess = spawn(backendPath, [], {
    env: { ...process.env, BACKEND_PORT: '8000' },
  })

  backendProcess.stdout.on('data', (d) => console.log('[backend]', d.toString()))
  backendProcess.stderr.on('data', (d) => console.error('[backend]', d.toString()))
  backendProcess.on('error', (err) => console.error('[backend] failed to start:', err))
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
    mainWindow.loadURL('http://localhost:5173')
    mainWindow.webContents.openDevTools()
  } else {
    mainWindow.loadFile(path.join(__dirname, '../dist/index.html'))
  }

  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url)
    return { action: 'deny' }
  })
}

app.whenReady().then(() => {
  startBackend()

  // Give the backend a moment to bind its port in production
  const delay = isDev ? 0 : 2500
  setTimeout(createWindow, delay)

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow()
  })
})

app.on('window-all-closed', () => {
  if (backendProcess) {
    backendProcess.kill()
    backendProcess = null
  }
  if (process.platform !== 'darwin') app.quit()
})

// IPC handlers
ipcMain.handle('get-app-version', () => app.getVersion())
ipcMain.handle('open-external', (_event, url) => shell.openExternal(url))
