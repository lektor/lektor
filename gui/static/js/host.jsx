'use strict'

import app from 'app'
import Tray from 'tray'
import BrowserWindow from 'browser-window'
import i18n from './i18n'

const BASE_PATH = __dirname.match(/^(.*?)[\/\\][^\/\\]+$/)[1]


function initWindow() {
  let loadedOnce = false;
  let win = new BrowserWindow({
    width: 400,
    height: 200,
    show: false,
    'title-bar-style': 'hidden-inset',
    resizable: false,
    fullscreen: false,
    'standard-window': false
  });

  // open delayed to hide the ugly flash
  win.webContents.on('did-finish-load', () => {
    setTimeout(() => {
      if (!loadedOnce) {
        win.show();
        loadedOnce = true;
      }
    }, 50);
  });

  win.loadUrl('file://' + BASE_PATH + '/index.html');
  win.on('closed', () => {
    // XXX: do something here
  });
  win.setVisibleOnAllWorkspaces(true);
  return win;
}

function initAppIcon(win) {
  let appIcon = new Tray(BASE_PATH + '/images/TrayTemplate.png');

  appIcon.on('clicked', (e, bounds) => {
    if (win.isVisible()) {
      win.hide();
    } else {
      win.show();
    }
  });

  appIcon.setToolTip('Lektor');
}

function main() {
  let filesToOpen = [];
  let win = null;
  let appIcon = null;
  let windowIsListening = false;

  let requestOpenFiles = (paths) => {
    if (win) {
      win.send('requestOpenFiles', paths);
    }
  }

  app.on('open-file', (event, pathToOpen) => {
    event.preventDefault();
    if (windowIsListening) {
      requestOpenFiles([pathToOpen]);
    } else {
      filesToOpen.push(pathToOpen);
    }
  });

  app.on('window-all-closed', () => {
    // delay this call so that we do not start unloading until the window
    // actually went away to hide a white flash.
    setTimeout(() => {
      app.quit();
    }, 0);
  });

  app.on('ready', () => {
    // we can only set it once the app is loaded as at least on osx the
    // locale is not initialized at an earlier point.
    i18n.setLanguageFromLocale(app.getLocale());

    win = initWindow();
    appIcon = initAppIcon(win);

    win.webContents.on('did-finish-load', () => {
      windowIsListening = true;
      if (filesToOpen.length > 0) {
        requestOpenFiles(filesToOpen);
      }
    });
  });
}

main();
