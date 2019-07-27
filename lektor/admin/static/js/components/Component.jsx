'use strict'
import dialogSystem from '../dialogSystem'
import BaseComponent from './BaseComponent'
import PropTypes from 'prop-types'

class Component extends BaseComponent {
  constructor (props, context) {
    super(props, context)
    this._unlistenBeforeLeavingRoute = null
  }

  /* helper function for forwarding props down the tree */
  getRoutingProps () {
    return {
      location: this.props.location,
      params: this.props.params,
      route: this.props.route,
      routeParams: this.props.routeParams,
      routes: this.props.routes
    }
  }

  /* helper that can generate a path to a rule */
  getPathToAdminPage (name, params) {
    let parts = this.props.routes.map((x) => x.name)
    if (name !== null) {
      if (name.substr(0, 1) === '.') {
        parts[parts.length - 1] = name.substr(1)
      } else {
        parts = name.split('.')
      }
    }

    const rv = []
    let node = this.props.routes[0]
    if (node.name !== parts.shift()) {
      return null
    }
    rv.push(node.path)

    parts.forEach((part) => {
      for (let i = 0; i < node.childRoutes.length; i++) {
        if (node.childRoutes[i].name === part) {
          node = node.childRoutes[i]
          rv.push(node.path)
          return
        }
      }
      node = null
    })

    return rv.join('/').replace(/:[a-zA-Z]+/g, (m) => {
      const key = m.substr(1)
      return params[key] || this.props.params[key]
    })
  }

  /* helper to transition to a specific page */
  transitionToAdminPage (name, params) {
    this.context.router.push(this.getPathToAdminPage(name, params))
  }

  componentDidMount () {
    super.componentDidMount()
    if (this.context.router !== undefined && this.props.route !== undefined) {
      this._unlistenBeforeLeavingRoute = this.context.router.setRouteLeaveHook(
        this.props.route, this.routerWillLeave.bind(this))
    }
  }

  componentWillUnmount () {
    super.componentWillUnmount()
    if (this._unlistenBeforeLeavingRoute) {
      this._unlistenBeforeLeavingRoute()
    }
  }

  routerWillLeave (nextLocation) {
    if (dialogSystem.preventNavigation()) {
      return false
    } else {
      dialogSystem.dismissDialog()
    }
  }
}

Component.contextTypes = {
  router: PropTypes.object.isRequired
}

export default Component
