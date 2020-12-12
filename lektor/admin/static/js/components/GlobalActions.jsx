import React from "react";
import RecordComponent from "./RecordComponent";
import { loadData, isMetaKey, getCanonicalUrl } from "../utils";
import { trans } from "../i18n";
import dialogSystem from "../dialogSystem";
import FindFiles from "../dialogs/findFiles";
import Publish from "../dialogs/publish";
import Refresh from "../dialogs/Refresh";
import makeRichPromise from "../richPromise";

function showFindFilesDialog() {
  dialogSystem.showDialog(FindFiles);
}

function showRefreshDialog() {
  dialogSystem.showDialog(Refresh);
}

function showPublishDialog() {
  dialogSystem.showDialog(Publish);
}

// meta+g is open find files
function onKeyPress(event) {
  if (event.which === 71 && isMetaKey(event)) {
    event.preventDefault();
    dialogSystem.showDialog(FindFiles);
  }
}

class GlobalActions extends RecordComponent {
  constructor(props) {
    super(props);
    this.state = {
      recordPathInfo: null,
    };
  }

  componentDidMount() {
    window.addEventListener("keydown", onKeyPress);
  }

  componentWillUnmount() {
    window.removeEventListener("keydown", onKeyPress);
  }

  _onCloseClick(e) {
    loadData(
      "/previewinfo",
      {
        path: this.getRecordPath(),
        alt: this.getRecordAlt(),
      },
      makeRichPromise
    ).then((resp) => {
      if (resp.url === null) {
        window.location.href = getCanonicalUrl("/");
      } else {
        window.location.href = getCanonicalUrl(resp.url);
      }
    });
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
          onClick={this._onCloseClick.bind(this)}
          title={trans("RETURN_TO_WEBSITE")}
        >
          <i className="fa fa-eye fa-fw" />
        </button>
      </div>
    );
  }
}

export default GlobalActions;
