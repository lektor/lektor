'use strict'

import React from 'react'
import { loadData, fsPathFromAdminObservedPath, getCanonicalUrl, urlPathsConsideredEqual } from '../utils'
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
    loadData('/previewinfo', { path: path, alt: alt }, null, makeRichPromise)
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

  componentDidUpdate (nextProps) {
    if (nextProps.match.params.path !== this.props.match.params.path) {
      this.setState({}, this.syncState.bind(this))
    }
    const frame = this.refs.iframe
    const intendedPath = this.getIntendedPath()
    if (intendedPath !== null) {
      const framePath = this.getFramePath()

      if (!urlPathsConsideredEqual(intendedPath, framePath)) {
        frame.src = getCanonicalUrl(intendedPath)
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
    return fsPathFromAdminObservedPath(
      frameLocation.pathname)
  }

  onFrameNavigated () {
    const fsPath = this.getFramePath()
    if (fsPath === null) {
      return
    }
    loadData('/matchurl', { url_path: fsPath }, null, makeRichPromise)
      .then((resp) => {
        if (resp.exists) {
          const urlPath = this.getUrlRecordPathWithAlt(resp.path, resp.alt)
          this.transitionToAdminPage('.preview', { path: urlPath })
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
