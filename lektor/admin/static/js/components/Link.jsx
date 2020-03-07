'use strict'

import PropTypes from 'prop-types'
import React from 'react'
import { NavLink } from 'react-router-dom'

function LektorLink (props) {
  let path = props.to
  if (path.substr(0, 1) !== '/') {
    path = $LEKTOR_CONFIG.admin_root + '/' + path
  }
  return (
    <NavLink to={path} activeClassName='active'>
      {props.children}
    </NavLink>
  )
}

LektorLink.propTypes = {
  to: PropTypes.string
}

export default LektorLink
