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
import { showErrorDialog } from "../error-dialog";

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

type Props = Pick<RecordProps, "record" | "history">;

export default class PreviewPage extends Component<Props, State> {
  iframe: RefObject<HTMLIFrameElement>;

  constructor(props: Props) {
    super(props);
    this.state = initialState;
    this.iframe = createRef();
    this.onFrameNavigated = this.onFrameNavigated.bind(this);
  }

  componentDidMount() {
    this.syncState();
  }

  shouldComponentUpdate(nextProps: Props) {
    return (
      getUrlRecordPath(this.props.record.path, this.props.record.alt) !==
        this.state.pageUrlFor ||
      nextProps.record.path !== this.props.record.path ||
      nextProps.record.alt !== this.props.record.alt
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
      }, showErrorDialog);
    }
  }

  componentDidUpdate(prevProps: Props) {
    if (
      prevProps.record.path !== this.props.record.path ||
      prevProps.record.alt !== this.props.record.alt
    ) {
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
      }, showErrorDialog);
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
