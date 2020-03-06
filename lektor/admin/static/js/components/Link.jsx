'use strict'

import PropTypes from 'prop-types'
import React from 'react'
import { Link } from 'react-router'

function LektorLink (props) {
  let path = props.to
  if (path.substr(0, 1) !== '/') {
    path = $LEKTOR_CONFIG.admin_root + '/' + path
  }
  return (
    <Link to={path} activeClassName='active'>
      {props.children}
    </Link>
  )
}

LektorLink.propTypes = {
  to: PropTypes.string
}

export default LektorLink
