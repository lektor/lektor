'use strict'

import BaseComponent from './BaseComponent'

class Component extends BaseComponent {
  /* helper that can generate a path to a rule */
  getPathToAdminPage (name, params) {
    // console.log('Get path to admin page ', name, 'with params', params)
    const parameters = {...this.props.match.params, ...params}
    // The paths are of the form '/admin/:path/:page'
    // TODO: page might be a constant for the router
    if (name !== null) {
      if (name.substr(0, 1) === '.') {
        parameters.page = name.substr(1)
      } else {
        throw new Error('TODO')
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
