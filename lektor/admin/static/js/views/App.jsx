'use strict'

import React from 'react'
import { Route } from 'react-router-dom'

import BreadCrumbs from '../components/BreadCrumbs'
import Sidebar from '../components/Sidebar'
import DialogSlot from '../components/DialogSlot'
import ServerStatus from '../components/ServerStatus'

function Header (props) {
  return (
    <header>
      <BreadCrumbs {...props}>
        <button
          type='button' className='navbar-toggle'
          data-toggle='offcanvas'
          data-target='.sidebar-block'
        >
          <span className='sr-only'>Toggle navigation</span>
          <span className='icon-list' />
          <span className='icon-list' />
          <span className='icon-list' />
        </button>
      </BreadCrumbs>
    </header>
  )
}

function App (props) {
  const fullPath = `${props.match.path}/:path/:page`
  return (
    <div className='application'>
      <ServerStatus />
      <Route path={fullPath} component={Header} />
      <div className='editor container'>
        <Route path={fullPath} component={DialogSlot} />
        <div className='sidebar-block block-offcanvas block-offcanvas-left'>
          <nav className='sidebar col-md-2 col-sm-3 sidebar-offcanvas'>
            <Route path={fullPath} component={Sidebar} />
          </nav>
          <div className='view col-md-10 col-sm-9'>
            {props.children}
          </div>
        </div>
      </div>
    </div>
  )
}

export default App
