import React, { createRef, RefObject } from "react";
import {
  fsPathFromAdminObservedPath,
  getCanonicalUrl,
  urlPathsConsideredEqual,
} from "../utils";
import { loadData } from "../fetch";
import RecordComponent, { RecordProps } from "../components/RecordComponent";
import { bringUpDialog } from "../richPromise";

const initialState = () => ({
  pageUrl: null,
  pageUrlFor: null,
});

type State = {
  pageUrl: string | null;
  pageUrlFor: string | null;
};

class PreviewPage extends RecordComponent<unknown, State> {
  iframe: RefObject<HTMLIFrameElement>;

  constructor(props: RecordProps) {
    super(props);
    this.state = initialState();
    this.iframe = createRef();
  }

  componentDidMount() {
    this.syncState();
  }

  shouldComponentUpdate(nextProps: RecordProps) {
    return (
      this.getUrlRecordPathWithAlt() !== this.state.pageUrlFor ||
      nextProps.match.params.path !== this.props.match.params.path
    );
  }

  syncState() {
    const alt = this.getRecordAlt();
    const path = this.getRecordPath();
    if (path === null) {
      this.setState(initialState);
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

  componentDidUpdate(prevProps: RecordProps) {
    if (prevProps.match.params.path !== this.props.match.params.path) {
      this.syncState();
    }
    const frame = this.iframe.current;
    const intendedPath = this.getIntendedPath();
    if (frame && intendedPath !== null) {
      const framePath = this.getFramePath();

      if (!urlPathsConsideredEqual(intendedPath, framePath)) {
        frame.src = getCanonicalUrl(intendedPath);
      }

      frame.onload = () => {
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
