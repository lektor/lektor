'use strict'

import Component from '../components/Component'

class Dash extends Component {
  componentDidMount () {
    super.componentDidMount()
    const rootPreview = $LEKTOR_CONFIG.admin_root + '/root/preview'
    this.context.router.push(rootPreview)
  }

  render () {
    return null
  }
}

export default Dash
