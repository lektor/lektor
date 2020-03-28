'use strict'

import BaseComponent from './BaseComponent'

class Component extends BaseComponent {
  /* helper that can generate a path to a rule */
  getPathToAdminPage (name, params) {
    const parameters = { ...this.props.match.params, ...params }
    if (name !== null) {
      if (name.substr(0, 1) === '.') {
        parameters.page = name.substr(1)
      } else {
        parameters.page = name
      }
    }

    return `${$LEKTOR_CONFIG.admin_root}/:path/:page`.replace(/:[a-zA-Z]+/g, (m) => {
      const key = m.substr(1)
      return parameters[key]
    })
  }

  /* helper to transition to a specific page */
  transitionToAdminPage (name, params) {
    const path = this.getPathToAdminPage(name, params)
    this.props.history.push(path)
  }
}

export default Component
