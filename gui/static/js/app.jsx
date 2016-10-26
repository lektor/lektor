'use strict'

import remote from 'remote'
import React from 'react'
import ReactDOM from 'react-dom'
import ipc from 'ipc'
import shell from 'shell'

import Component from './components/Component'
import { LektorInterop, installShellCommands } from './lektorInterop'
import i18n from './i18n'
import { isDevMode, attachDevMenu } from './utils'

const app = remote.require('app')
const dialog = remote.require('dialog')
const Menu = remote.require('menu')


i18n.setLanguageFromLocale(app.getLocale())


class App extends Component {

  constructor(props) {
    super(props);
    this.state = {
      lektorState: 'initializing',
      projectPath: null,
      projectState: 'closed',
      projectData: null,
      projectServer: null,
      projectServerStatus: [],
      buttonTitle: null
    };

    this.onRequestOpenFiles = this.onRequestOpenFiles.bind(this)
    this.onBeforeUnload = this.onBeforeUnload.bind(this)
    this.lektorInterop = new LektorInterop()
  }

  openProject(path, filesToOpen) {
    this.closeProject();
    this.setState({
      projectPath: path,
      projectState: 'loading',
      projectData: null,
      projectServerStatus: []
    }, () => {
      this.lektorInterop.analyzeProject(path).then((project) => {
        if (project === null) {
          this.setState({
            projectState: 'failed'
          });
        } else {
          this.setState({
            projectState: 'loaded',
            projectData: project,
          }, this.openFilesAsync.bind(this, filesToOpen))
          this.spawnServerForProject(project.project_path)
        }
      }, (failure) => {
        this.setState({
          projectState: 'failed'
        });
        dialog.showErrorBox(i18n.trans('FAILED_TO_LAUNCH_LEKTOR'),
                            failure.toString());
      });
    });
  }

  browseForProject() {
    dialog.showOpenDialog(null, {
      title: 'Open Lektor Project',
      filters: [
        {
          name: 'Lektor Projects',
          extensions: ['lektorproject']
        }
      ],
      properties: ['openFile']
    }, (files) => {
      if (files) {
        this.openProject(files[0]);
      }
    });
  }

  closeProject() {
    if (this.state.projectServer) {
      this.state.projectServer.shutdown()
    }
    this.setState({
      projectPath: null,
      projectState: 'closed',
      projectData: null,
      projectServerStatus: [],
      filesToOpen: []
    });
  }

  openFilesAsync(filesToOpen) {
    if ((filesToOpen || []).length == 0) {
      return;
    }

    let projectPath = this.state.projectData
      ? this.state.projectData.project_path : null

    function couldNotOpen(message) {
      dialog.showErrorBox(i18n.trans('FAILED_TO_OPEN_CONTENT_FILE'),
                          message.toString())
    }

    this.lektorInterop.discoverProjectForFiles(filesToOpen)
      .then((result) => {
        if (result.success) {
          if (projectPath !== null &&
              result.project.project_path == projectPath) {
            let server = this.state.projectServer;
            if (server) {
              result.paths.forEach((path) => {
                shell.openExternal(server.getAdminEditUrl(path));
              });
            }
          } else if (projectPath === null) {
            this.openProject(result.project.project_path, filesToOpen);
          } else {
            let btn = dialog.showMessageBox(null, {
              type: 'question',
              buttons: [i18n.trans('YES'), i18n.trans('NO')],
              cancelId: 1,
              message: i18n.trans('OPEN_OTHER_PROJECT'),
              detail: i18n.trans('OPEN_OTHER_PROJECT_QUESTION').replace(
                /%s/g, result.project.name)
            });
            if (btn == 0) {
              this.openProject(result.project.project_path, filesToOpen);
            }
          }
        } else {
          couldNotOpen(result.error);
        }
      }, (failure) => {
        couldNotOpen(failure);
      });
  }

  browseWebsite() {
    let server = this.state.projectServer;
    if (server) {
      shell.openExternal(server.getUrl());
    }
  }

  viewAdminPanel() {
    let server = this.state.projectServer;
    if (server) {
      shell.openExternal(server.getAdminUrl());
    }
  }

  spawnServerForProject(projectPath) {
    if (this.state.projectServer !== null) {
      this.state.projectServer.shutdown();
    }
    this.state.projectServer = this.lektorInterop.spawnServer(projectPath, {
      statusLineCallback: (statusLine) => {
        this.setState({
          projectServerStatus: Array.prototype.concat.call(
            this.state.projectServerStatus, statusLine)
        });
      }
    });
  }

  uiIsLocked() {
    return this.state.projectState === 'loading';
  }

  componentDidMount() {
    super.componentDidMount();
    ipc.on('requestOpenFiles', this.onRequestOpenFiles);
    window.addEventListener('beforeunload', this.onBeforeUnload);

    let menu = this.buildMenu();
    Menu.setApplicationMenu(menu);

    this.resizeWindow();
    this.lektorInterop.checkLektor()
      .then((version) => {
        this.setState({
          lektorState: 'initialized'
        });
      }, (failure) => {
        this.setState({
          lektorState: 'failed'
        });
        dialog.showErrorBox(i18n.trans('FAILED_TO_LAUNCH_LEKTOR'),
                            failure.toString());
        app.quit();
      });
  }

  componentWillUnmount() {
    window.removeEventListener('beforeunload', this.onBeforeUnload);
    ipc.removeListener('requestOpenFiles', this.onRequestOpenFiles);
    super.componentWillUnmount();
  }

  componentDidUpdate() {
    super.componentDidUpdate();
    if (this.refs.log) {
      this.refs.log.scrollTop = this.refs.log.scrollHeight;
    }
    this.resizeWindow();
  }

  buildMenu() {
    let submenu = [{
      label: i18n.trans('INSTALL_SHELL_COMMAND'),
      click: () => {
        let btn = dialog.showMessageBox(null, {
          type: 'question',
          buttons: [i18n.trans('YES'), i18n.trans('NO')],
          cancelId: 1,
          message: i18n.trans('INSTALL_SHELL_COMMAND'),
          detail: i18n.trans('INSTALL_SHELL_COMMAND_QUESTION')
        });
        if (btn == 0) {
          if (!installShellCommands()) {
            dialog.showErrorBox(i18n.trans('ERROR'),
                                i18n.trans('FAILED_TO_INSTALL_SHELL_COMMANDS'));
          } else {
            dialog.showMessageBox(null, {
              type: 'info',
              buttons: [i18n.trans('OK')],
              message: i18n.trans('OPERATION_SUCCESS'),
              detail: i18n.trans('INSTALL_SHELL_COMMAND_SUCCESS'),
            });
          }
        }
      }
    }];

    if (isDevMode()) {
      attachDevMenu(submenu);
    }
    submenu.push({
      type: 'separator'
    }),
    submenu.push({
      label: i18n.trans('QUIT_LEKTOR'),
      accelerator: 'Command+Q',
      click: () => { app.quit(); }
    });

    return Menu.buildFromTemplate([
      {
        label: process.platform == 'darwin' ? app.getName() : i18n.trans('FILE'),
        submenu: submenu,
      },
      {
        label: i18n.trans('EDIT'),
        submenu: [
          {
            label: i18n.trans('UNDO'),
            accelerator: 'CmdOrCtrl+Z',
            role: 'undo'
          },
          {
            label: i18n.trans('REDO'),
            accelerator: 'Shift+CmdOrCtrl+Z',
            role: 'redo'
          },
          {
            type: 'separator'
          },
          {
            label: i18n.trans('CUT'),
            accelerator: 'CmdOrCtrl+X',
            role: 'cut'
          },
          {
            label: i18n.trans('COPY'),
            accelerator: 'CmdOrCtrl+C',
            role: 'copy'
          },
          {
            label: i18n.trans('PASTE'),
            accelerator: 'CmdOrCtrl+V',
            role: 'paste'
          },
          {
            label: i18n.trans('SELECT_ALL'),
            accelerator: 'CmdOrCtrl+A',
            role: 'selectall'
          },
        ]
      },
      {
        label: i18n.trans('HELP'),
        role: 'help',
        submenu: [
          {
            label: i18n.trans('VISIT_WEBSITE'),
            click: () => {
              shell.openExternal('https://www.getlektor.com/');
            }
          }
        ]
      },
    ]);
  }

  resizeWindow() {
    let win = remote.getCurrentWindow();
    let [width, height] = win.getContentSize();
    let app = this.refs.app;
    win.setContentSize(width, app.scrollHeight);
  }

  onRequestOpenFiles(pathsToOpen) {
    let projectToOpen = null;
    const filesToOpen = [];
    pathsToOpen.forEach((path) => {
      if (path.match(/\.lektorproject$/)) {
        projectToOpen = path;
      } else {
        filesToOpen.push(path);
      }
    });

    if (projectToOpen !== null) {
      this.openProject(pathsToOpen[0], filesToOpen);
    } else {
      this.openFilesAsync(filesToOpen);
    }
  }

  onBeforeUnload(event) {
    let server = this.state.projectServer;
    if (server !== null) {
      server.shutdown();
    }
  }

  showButtonTitle(title) {
    this.setState({
      buttonTitle: title
    });
  }

  renderNav() {
    let rv = [];
    const uiLock = this.uiIsLocked();

    let addButton = (state, icon, title, callback) => {
      let disabled = uiLock;
      if (state !== null && this.state.projectState === state) {
        disabled = true;
      }

      rv.push(
        <button
          className="list-group-item"
          disabled={disabled}
          onClick={callback}
          onMouseMove={this.showButtonTitle.bind(this, title)}
          onMouseLeave={this.showButtonTitle.bind(this, null)}
          key={rv.length}><i className={'fa fa-' + icon}></i></button>
      );
    };

    addButton(null, 'folder-open-o', i18n.trans('OPEN_PROJECT'), this.browseForProject.bind(this));
    addButton('closed', 'times', i18n.trans('CLOSE_PROJECT'), this.closeProject.bind(this));
    addButton('closed', 'eye', i18n.trans('BROWSE_WEBSITE'), this.browseWebsite.bind(this));
    addButton('closed', 'pencil', i18n.trans('VIEW_ADMIN_PANEL'), this.viewAdminPanel.bind(this));
    addButton(null, 'power-off', i18n.trans('QUIT'), () => { app.quit(); });

    return rv;
  }

  renderProjectStatus() {
    if (this.state.projectState === 'closed') {
      return null;
    } else if (this.state.projectState === 'failed') {
      return <p>{i18n.trans('FAILED_TO_LOAD_PROJECT')}</p>;
    } else if (this.state.projectState === 'loading') {
      return <p>{i18n.trans('LOADING_PROJECT')}</p>;
    }
    return (
      <div className="project-status">
        <dl>
          <dt>{i18n.trans('PROJECT')}</dt>
          <dd>{this.state.projectData.name}</dd>
        </dl>
        <ul className="log" ref="log">{
          this.state.projectServerStatus.map((item, idx) => {
            return <li key={idx}>{item}</li>;
          })
        }</ul>
      </div>
    );
  }

  renderTitle() {
    if (process.platform != 'win32') {
      return ( <h1>Lektor</h1>);
    }
    return null;
  }

  renderLektorInit() {
    let spinner = null;
    if (this.state.lektorState === 'initializing') {
      spinner = <p className="spinner">
        <i className="fa fa-spin fa-spinner fa-3x"></i>
      </p>;
    }
    return (
      <div className="app app-initializing" ref="app">
        <p>{i18n.trans('INITIALIZING_LEKTOR')}</p>
        {spinner}
      </div>
    );
  }

  render() {
    if (this.state.lektorState !== 'initialized') {
      return this.renderLektorInit();
    }
    return (
      <div className="app" ref="app">
        <div className="main-nav">
          {this.renderTitle()}
          <div className="list-group">
            {this.renderNav()}
          </div>
          <p className="explanation">
            {this.state.buttonTitle}
          </p>
        </div>
        {this.renderProjectStatus()}
      </div>
    );
  }
}

ReactDOM.render(<App />, document.getElementById('root'));
