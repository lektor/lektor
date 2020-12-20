import React, { createRef, RefObject, SyntheticEvent } from "react";
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

function getIframePath(iframe: HTMLIFrameElement): string | null {
  const frameLocation = iframe.contentWindow?.location;
  if (!frameLocation) {
    return null;
  }
  return frameLocation.href === "about:blank"
    ? frameLocation.href
    : fsPathFromAdminObservedPath(frameLocation.pathname);
}

export default class PreviewPage extends RecordComponent<unknown, State> {
  iframe: RefObject<HTMLIFrameElement>;

  constructor(props: RecordProps) {
    super(props);
    this.state = initialState();
    this.iframe = createRef();
    this.onFrameNavigated = this.onFrameNavigated.bind(this);
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

  componentDidUpdate(prevProps: RecordProps) {
    if (prevProps.match.params.path !== this.props.match.params.path) {
      this.syncState();
    }
    const frame = this.iframe.current;
    const intendedPath =
      this.state.pageUrlFor === this.getUrlRecordPathWithAlt()
        ? this.state.pageUrl
        : null;
    if (frame && intendedPath !== null) {
      const framePath = getIframePath(frame);

      if (!urlPathsConsideredEqual(intendedPath, framePath)) {
        frame.src = getCanonicalUrl(intendedPath);
      }
    }
  }

  onFrameNavigated(event: SyntheticEvent<HTMLIFrameElement>) {
    const fsPath = getIframePath(event.currentTarget);
    if (fsPath !== null) {
      loadData("/matchurl", { url_path: fsPath }).then((resp) => {
        if (resp.exists) {
          const urlPath = this.getUrlRecordPathWithAlt(resp.path, resp.alt);
          this.transitionToAdminPage("preview", urlPath);
        }
      }, bringUpDialog);
    }
  }

  render() {
    return (
      <div className="preview">
        <iframe ref={this.iframe} onLoad={this.onFrameNavigated} />
      </div>
    );
  }
}
