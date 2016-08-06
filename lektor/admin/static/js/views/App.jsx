'use strict'

import React from 'react'
import BreadCrumbs from '../components/BreadCrumbs'
import Sidebar from '../components/Sidebar'
import Component from '../components/Component'
import DialogSlot from '../components/DialogSlot'
import ServerStatus from '../components/ServerStatus'
import dialogSystem from '../dialogSystem'
import {DialogChangedEvent} from '../events'
import hub from '../hub'


class App extends Component {

  render() {
    return (
      <div className="application">
        <ServerStatus/>
        <header>
          <BreadCrumbs {...this.getRoutingProps()}>
            <button type="button" className="navbar-toggle"
                data-toggle="offcanvas"
                data-target=".sidebar-block">
              <span className="sr-only">Toggle navigation</span>
              <span className="icon-list"></span>
              <span className="icon-list"></span>
              <span className="icon-list"></span>
            </button>
          </BreadCrumbs>
        </header>
        <div className="editor container">
          <DialogSlot {...this.getRoutingProps()}/>
          <div className="sidebar-block block-offcanvas block-offcanvas-left">
            <nav className="sidebar col-md-2 col-sm-3 sidebar-offcanvas">
              <Sidebar {...this.getRoutingProps()}/>
            </nav>
            <div className="view col-md-10 col-sm-9">
              {this.props.children}
            </div>
          </div>
        </div>
      </div>
    );
  }
}

export default App
