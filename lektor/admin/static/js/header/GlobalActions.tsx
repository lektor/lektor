import React from "react";
import RecordComponent, { RecordProps } from "../components/RecordComponent";
import { isMetaKey, getCanonicalUrl } from "../utils";
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

function onKeyPress(event: KeyboardEvent) {
  // Command+g/Ctrl+g to open the find files dialog.
  if (event.key === "g" && isMetaKey(event)) {
    event.preventDefault();
    dialogSystem.showDialog(FindFiles);
  }
}

class GlobalActions extends RecordComponent<RecordProps, unknown> {
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
      path: this.getRecordPath(),
      alt: this.getRecordAlt(),
    }).then((resp) => {
      if (resp.url === null) {
        window.location.href = getCanonicalUrl("/");
      } else {
        window.location.href = getCanonicalUrl(resp.url);
      }
    }, bringUpDialog);
  }

  render() {
    return (
      <div className="btn-group">
        <button
          className="btn btn-default"
          onClick={showFindFilesDialog}
          title={trans("FIND_FILES")}
        >
          <i className="fa fa-search fa-fw" />
        </button>
        <button
          className="btn btn-default"
          onClick={showPublishDialog}
          title={trans("PUBLISH")}
        >
          <i className="fa fa-cloud-upload fa-fw" />
        </button>
        <button
          className="btn btn-default"
          onClick={showRefreshDialog}
          title={trans("REFRESH_BUILD")}
        >
          <i className="fa fa-refresh fa-fw" />
        </button>
        <button
          className="btn btn-default"
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
