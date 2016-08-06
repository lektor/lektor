'use strict'

import React from 'react'
import Router from 'react-router'
import utils from '../utils'
import RecordComponent from '../components/RecordComponent'


class PreviewPage extends RecordComponent {

  constructor(props) {
    super(props);
    this.state = {
      pageUrl: null,
      pageUrlFor: null
    };
  }

  componentWillReceiveProps(nextProps) {
    super.componentWillReceiveProps(nextProps);
    this.setState({}, this.syncState.bind(this));
  }

  componentDidMount() {
    super.componentDidMount();
    this.syncState();
  }

  shouldComponentUpdate() {
    return this.getUrlRecordPathWithAlt() != this.state.pageUrlFor;
  }

  syncState() {
    var alt = this.getRecordAlt();
    var path = this.getRecordPath();
    if (path === null) {
      this.setState(this.getInitialState());
      return;
    }

    var recordUrl = this.getUrlRecordPathWithAlt();
    utils.loadData('/previewinfo', {path: path, alt: alt})
      .then((resp) => {
        this.setState({
          pageUrl: resp.url,
          pageUrlFor: recordUrl
        });
      });
  }

  getIntendedPath() {
    if (this.state.pageUrlFor == this.getUrlRecordPathWithAlt()) {
      return this.state.pageUrl;
    }
    return null;
  }

  componentDidUpdate() {
    var frame = this.refs.iframe;
    var intendedPath = this.getIntendedPath();
    if (intendedPath !== null) {
      var framePath = this.getFramePath();

      if (!utils.urlPathsConsideredEqual(intendedPath, framePath)) {
        frame.src = utils.getCanonicalUrl(intendedPath);
      }

      frame.onload = (event) => {
        this.onFrameNavigated();
      };
    }
  }

  getFramePath() {
    var frameLocation = this.refs.iframe.contentWindow.location;
    if (frameLocation.href === 'about:blank') {
        return frameLocation.href;
    }
    return utils.fsPathFromAdminObservedPath(
      frameLocation.pathname);
  }

  onFrameNavigated() {
    var fsPath = this.getFramePath();
    if (fsPath === null) {
      return;
    }
    utils.loadData('/matchurl', {url_path: fsPath})
      .then((resp) => {
        if (resp.exists) {
          var urlPath = this.getUrlRecordPathWithAlt(resp.path, resp.alt);
          this.transitionToAdminPage('.preview', {path: urlPath});
        }
      });
  }

  render() {
    return (
      <div className="preview">
        <iframe ref="iframe"></iframe>
      </div>
    );
  }
}

export default PreviewPage
