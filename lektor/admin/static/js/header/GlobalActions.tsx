import React, { Component } from "react";
import { RecordProps } from "../components/RecordComponent";
import { getCanonicalUrl, keyboardShortcutHandler } from "../utils";
import { loadData } from "../fetch";
import { trans } from "../i18n";
import dialogSystem from "../dialogSystem";
import FindFiles from "../dialogs/findFiles";
import Publish from "../dialogs/publish";
import Refresh from "../dialogs/Refresh";
import { bringUpDialog } from "../richPromise";

function showFindFilesDialog() {
  dialogSystem.showDialog(FindFiles);
}

function showRefreshDialog() {
  dialogSystem.showDialog(Refresh);
}

function showPublishDialog() {
  dialogSystem.showDialog(Publish);
}

const onKeyPress = keyboardShortcutHandler(
  { key: "Control+g", mac: "Meta+g", preventDefault: true },
  () => dialogSystem.showDialog(FindFiles)
);

class GlobalActions extends Component<RecordProps, unknown> {
  constructor(props: RecordProps) {
    super(props);
    this.onCloseClick = this.onCloseClick.bind(this);
  }

  componentDidMount() {
    window.addEventListener("keydown", onKeyPress);
  }

  componentWillUnmount() {
    window.removeEventListener("keydown", onKeyPress);
  }

  onCloseClick() {
    loadData("/previewinfo", {
      path: this.props.record.path,
      alt: this.props.record.alt,
    }).then((resp) => {
      if (resp.url === null) {
        window.location.href = getCanonicalUrl("/");
      } else {
        window.location.href = getCanonicalUrl(resp.url);
      }
    }, bringUpDialog);
  }

  render() {
    const buttonClass = "btn btn-secondary border";
    return (
      <div className="btn-group">
        <button
          type="button"
          className={buttonClass}
          onClick={showFindFilesDialog}
          title={trans("FIND_FILES")}
        >
          <i className="fa fa-search fa-fw" />
        </button>
        <button
          type="button"
          className={buttonClass}
          onClick={showPublishDialog}
          title={trans("PUBLISH")}
        >
          <i className="fa fa-cloud-upload fa-fw" />
        </button>
        <button
          type="button"
          className={buttonClass}
          onClick={showRefreshDialog}
          title={trans("REFRESH_BUILD")}
        >
          <i className="fa fa-refresh fa-fw" />
        </button>
        <button
          type="button"
          className={buttonClass}
          onClick={this.onCloseClick}
          title={trans("RETURN_TO_WEBSITE")}
        >
          <i className="fa fa-eye fa-fw" />
        </button>
      </div>
    );
  }
}

export default GlobalActions;
