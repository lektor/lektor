import React, { Component, createRef, RefObject, SyntheticEvent } from "react";
import {
  fsPathFromAdminObservedPath,
  getCanonicalUrl,
  urlPathsConsideredEqual,
} from "../utils";
import { loadData } from "../fetch";
import {
  getUrlRecordPath,
  pathToAdminPage,
  RecordProps,
} from "../components/RecordComponent";
import { bringUpDialog } from "../richPromise";

function getIframePath(iframe: HTMLIFrameElement): string | null {
  const frameLocation = iframe.contentWindow?.location;
  if (!frameLocation) {
    return null;
  }
  return frameLocation.href === "about:blank"
    ? frameLocation.href
    : fsPathFromAdminObservedPath(frameLocation.pathname);
}

type State = {
  pageUrl: string | null;
  pageUrlFor: string | null;
};

const initialState = {
  pageUrl: null,
  pageUrlFor: null,
};

export default class PreviewPage extends Component<RecordProps, State> {
  iframe: RefObject<HTMLIFrameElement>;

  constructor(props: RecordProps) {
    super(props);
    this.state = initialState;
    this.iframe = createRef();
    this.onFrameNavigated = this.onFrameNavigated.bind(this);
  }

  componentDidMount() {
    this.syncState();
  }

  shouldComponentUpdate(nextProps: RecordProps) {
    return (
      getUrlRecordPath(this.props.record.path, this.props.record.alt) !==
        this.state.pageUrlFor ||
      nextProps.match.params.path !== this.props.match.params.path
    );
  }

  syncState() {
    const { alt, path } = this.props.record;
    if (path === null) {
      this.setState(initialState);
    } else {
      loadData("/previewinfo", { path, alt }).then((resp) => {
        this.setState({
          pageUrl: resp.url,
          pageUrlFor: getUrlRecordPath(path, alt),
        });
      }, bringUpDialog);
    }
  }

  componentDidUpdate(prevProps: RecordProps) {
    if (prevProps.match.params.path !== this.props.match.params.path) {
      this.syncState();
    }
    const frame = this.iframe.current;
    const intendedPath =
      this.state.pageUrlFor ===
      getUrlRecordPath(this.props.record.path, this.props.record.alt)
        ? this.state.pageUrl
        : null;
    if (frame && intendedPath) {
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
          const urlPath = getUrlRecordPath(resp.path, resp.alt);
          this.props.history.push(pathToAdminPage("preview", urlPath));
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
