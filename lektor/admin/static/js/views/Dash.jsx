'use strict'

import React from 'react'
import Component from '../components/Component';

class Dash extends Component {

  componentDidMount() {
    super.componentDidMount()
    const rootPreview = $LEKTOR_CONFIG.admin_root + '/root/preview'
    this.props.history.pushState(null, rootPreview)
  }

  render() {
    return null
  }
}

export default Dash
