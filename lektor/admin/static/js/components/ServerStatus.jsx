'use strict'

import React from 'react'
import { loadData } from '../utils'
import i18n from '../i18n'
import makeRichPromise from '../richPromise'

class ServerStatus extends React.Component {
  constructor (props) {
    super(props)
    this.state = {
      serverIsUp: true,
      projectId: null
    }

    this.intervalId = null
    this.onInterval = this.onInterval.bind(this)
  }

  componentDidMount () {
    this.intervalId = window.setInterval(this.onInterval, 2000)
  }

  componentWillUnmount () {
    if (this.intervalId !== null) {
      window.clearInterval(this.intervalId)
      this.intervalId = null
    }
  }

  onInterval () {
    loadData('/ping', {}, null, makeRichPromise)
      .then((resp) => {
        if (this.state.projectId === null) {
          this.setState({
            projectId: resp.project_id
          })
        }
        this.setState({
          serverIsUp: this.state.projectId === resp.project_id
        })
      }, () => {
        this.setState({
          serverIsUp: false
        })
      })
  }

  render () {
    if (this.state.serverIsUp) {
      return null
    }
    return (
      <div className='server-down-panel'>
        <div className='server-down-dialog'>
          <h3>{i18n.trans('ERROR_SERVER_UNAVAILABLE')}</h3>
          <p>{i18n.trans('ERROR_SERVER_UNAVAILABLE_MESSAGE')}</p>
        </div>
      </div>
    )
  }
}

export default ServerStatus
