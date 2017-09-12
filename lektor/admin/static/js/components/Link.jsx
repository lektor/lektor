'use strict'

import PropTypes from 'prop-types'
import React from 'react'
import { Link } from 'react-router'
import Component from './Component'

class LektorLink extends Component {
  render () {
    let path = this.props.to
    if (path.substr(0, 1) !== '/') {
      path = $LEKTOR_CONFIG.admin_root + '/' + path
    }
    return (
      <Link to={path} activeClassName='active'>
        {this.props.children}
      </Link>
    )
  }
}

LektorLink.propTypes = {
  to: PropTypes.string
}

module.exports = LektorLink
