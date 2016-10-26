'use strict'

import React from 'react'
import ReactRouter from 'react-router'
import Component from './Component'


class Link extends Component {

  render() {
    let path = this.props.to;
    if (path.substr(0, 1) !== '/') {
      path = $LEKTOR_CONFIG.admin_root + '/' + path;
    }
    return (
      <ReactRouter.Link to={path} activeClassName="active">
        {this.props.children}
      </ReactRouter.Link>
    );
  }
}

Link.propTypes = {
  to: React.PropTypes.string
}


module.exports = Link
