'use strict'

import React from 'react'
import ReactDOM from 'react-dom'
import { BrowserRouter as Router, Route, Switch } from 'react-router-dom'
import i18n from './i18n'

/* eslint-disable no-unused-vars */
import Bootstrap from 'bootstrap'
import BootstrapExtras from './bootstrap-extras'
import FACss from 'font-awesome/css/font-awesome.css'

// polyfill for internet explorer
import EventSource from 'event-source-polyfill'
/* eslint-enable no-unused-vars */

// route targets
import App from './views/App'
import EditPage from './views/EditPage'
import DeletePage from './views/DeletePage'
import PreviewPage from './views/PreviewPage'
import AddChildPage from './views/AddChildPage'
import AddAttachmentPage from './views/AddAttachmentPage'

i18n.currentLanguage = $LEKTOR_CONFIG.lang

function BadRoute (props) {
  return (
    <div>
      <h2>Nothing to see here</h2>
      <p>There is really nothing to see here.</p>
    </div>
  )
}

function Main (props) {
  const { path } = props.match
  return (
    <App {...props}>
      <Switch>
        <Route name='edit' path={`${path}/:path/edit`} component={EditPage} />
        <Route name='delete' path={`${path}/:path/delete`} component={DeletePage} />
        <Route name='preview' path={`${path}/:path/preview`} component={PreviewPage} />
        <Route name='add-child' path={`${path}/:path/add-child`} component={AddChildPage} />
        <Route name='upload' path={`${path}/:path/upload`} component={AddAttachmentPage} />
        <Route component={BadRoute} />
      </Switch>
    </App>
  )
}

const dash = document.getElementById('dash')

if (dash) {
  ReactDOM.render((
    <Router>
      <Route name='app' path={$LEKTOR_CONFIG.admin_root} component={Main} />
    </Router>
  ), dash)
}
