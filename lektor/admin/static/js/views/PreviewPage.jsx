import React, { createRef } from "react";
import {
  loadData,
  fsPathFromAdminObservedPath,
  getCanonicalUrl,
  urlPathsConsideredEqual,
} from "../utils";
import RecordComponent from "../components/RecordComponent";
import { bringUpDialog } from "../richPromise";

class PreviewPage extends RecordComponent {
  constructor(props) {
    super(props);
    this.state = {
      pageUrl: null,
      pageUrlFor: null,
    };
    this.iframe = createRef();
  }

  componentDidMount() {
    this.syncState();
  }

  shouldComponentUpdate(nextProps) {
    return (
      this.getUrlRecordPathWithAlt() !== this.state.pageUrlFor ||
      nextProps.match.params.path !== this.props.match.params.path
    );
  }

  syncState() {
    const alt = this.getRecordAlt();
    const path = this.getRecordPath();
    if (path === null) {
      this.setState(this.getInitialState());
      return;
    }

    const recordUrl = this.getUrlRecordPathWithAlt();
    loadData("/previewinfo", { path: path, alt: alt }).then((resp) => {
      this.setState({
        pageUrl: resp.url,
        pageUrlFor: recordUrl,
      });
    }, bringUpDialog);
  }

  getIntendedPath() {
    if (this.state.pageUrlFor === this.getUrlRecordPathWithAlt()) {
      return this.state.pageUrl;
    }
    return null;
  }

  componentDidUpdate(prevProps) {
    if (prevProps.match.params.path !== this.props.match.params.path) {
      this.setState({}, this.syncState.bind(this));
    }
    const frame = this.iframe.current;
    const intendedPath = this.getIntendedPath();
    if (intendedPath !== null) {
      const framePath = this.getFramePath();

      if (!urlPathsConsideredEqual(intendedPath, framePath)) {
        frame.src = getCanonicalUrl(intendedPath);
      }

      frame.onload = (event) => {
        this.onFrameNavigated();
      };
    }
  }

  getFramePath() {
    const frameLocation = this.iframe.current.contentWindow.location;
    if (frameLocation.href === "about:blank") {
      return frameLocation.href;
    }
    return fsPathFromAdminObservedPath(frameLocation.pathname);
  }

  onFrameNavigated() {
    const fsPath = this.getFramePath();
    if (fsPath === null) {
      return;
    }
    loadData("/matchurl", { url_path: fsPath }).then((resp) => {
      if (resp.exists) {
        const urlPath = this.getUrlRecordPathWithAlt(resp.path, resp.alt);
        this.transitionToAdminPage("preview", urlPath);
      }
    }, bringUpDialog);
  }

  render() {
    return (
      <div className="preview">
        <iframe ref={this.iframe} />
      </div>
    );
  }
}

export default PreviewPage;
