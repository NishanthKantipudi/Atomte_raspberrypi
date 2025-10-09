const { app, BrowserWindow } = require('electron');
const path = require('path');

function createWindow() {
    const code= process.argv[2] || '';
  const win = new BrowserWindow({
    width: 800,
    height: 600,
    fullscreen: true,          // opens in full-screen
    autoHideMenuBar: true,     // hides menu bar
    webPreferences: {
      nodeIntegration: false,  // keep it false for security
      contextIsolation: true
    }
  });
  console.log('Received code:', code);

  // Load the React app
  // If using a local server
  win.loadURL('http://localhost:3000?code=' + code);

  // If using build folder
  // win.loadFile(path.join(__dirname, 'build', 'index.html'));
}

app.whenReady().then(() => {
  createWindow();

  app.on('activate', function () {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', function () {
  if (process.platform !== 'darwin') app.quit();
});
