'use strict'

import React from 'react'
import utils from '../utils'
import RecordComponent from '../components/RecordComponent'
import makeRichPromise from '../richPromise'

class PreviewPage extends RecordComponent {
  constructor (props) {
    super(props)
    this.state = {
      pageUrl: null,
      pageUrlFor: null
    }
  }

  componentWillReceiveProps (nextProps) {
    super.componentWillReceiveProps(nextProps)
    this.setState({}, this.syncState.bind(this))
  }

  componentDidMount () {
    super.componentDidMount()
    this.syncState()
  }

  shouldComponentUpdate () {
    return this.getUrlRecordPathWithAlt() !== this.state.pageUrlFor
  }

  syncState () {
    const alt = this.getRecordAlt()
    const path = this.getRecordPath()
    if (path === null) {
      this.setState(this.getInitialState())
      return
    }

    const recordUrl = this.getUrlRecordPathWithAlt()
    utils.loadData('/previewinfo', {path: path, alt: alt}, null, makeRichPromise)
      .then((resp) => {
        this.setState({
          pageUrl: resp.url,
          pageUrlFor: recordUrl
        })
      })
  }

  getIntendedPath () {
    if (this.state.pageUrlFor === this.getUrlRecordPathWithAlt()) {
      return this.state.pageUrl
    }
    return null
  }

  componentDidUpdate () {
    const frame = this.refs.iframe
    const intendedPath = this.getIntendedPath()
    if (intendedPath !== null) {
      const framePath = this.getFramePath()

      if (!utils.urlPathsConsideredEqual(intendedPath, framePath)) {
        frame.src = utils.getCanonicalUrl(intendedPath)
      }

      frame.onload = (event) => {
        this.onFrameNavigated()
      }
    }
  }

  getFramePath () {
    const frameLocation = this.refs.iframe.contentWindow.location
    if (frameLocation.href === 'about:blank') {
      return frameLocation.href
    }
    return utils.fsPathFromAdminObservedPath(
      frameLocation.pathname)
  }

  onFrameNavigated () {
    const fsPath = this.getFramePath()
    if (fsPath === null) {
      return
    }
    utils.loadData('/matchurl', {url_path: fsPath}, null, makeRichPromise)
      .then((resp) => {
        if (resp.exists) {
          const urlPath = this.getUrlRecordPathWithAlt(resp.path, resp.alt)
          this.transitionToAdminPage('.preview', {path: urlPath})
        }
      })
  }

  render () {
    return (
      <div className='preview'>
        <iframe ref='iframe' />
      </div>
    )
  }
}

export default PreviewPage
