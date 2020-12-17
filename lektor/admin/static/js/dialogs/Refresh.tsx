import React from "react";
import SlideDialog from "../components/SlideDialog";
import { loadData } from "../fetch";
import { trans } from "../i18n";
import dialogSystem from "../dialogSystem";
import { bringUpDialog } from "../richPromise";

type State = "IDLE" | "DONE" | "CLEANING";

export default class Refresh extends React.Component<
  unknown,
  { currentState: State }
> {
  constructor(props: unknown) {
    super(props);
    this.state = {
      currentState: "IDLE",
    };
  }

  preventNavigation() {
    return !this.isSafeToNavigate();
  }

  isSafeToNavigate() {
    return (
      this.state.currentState === "IDLE" || this.state.currentState === "DONE"
    );
  }

  onRefresh() {
    this.setState({
      currentState: "CLEANING",
    });
    loadData("/clean", null, { method: "POST" }).then(() => {
      this.setState({
        currentState: "DONE",
      });
    }, bringUpDialog);
  }

  onCancel() {
    dialogSystem.dismissDialog();
  }

  render() {
    let progress = null;
    if (this.state.currentState !== "IDLE") {
      progress = (
        <div>
          <h3>
            {this.state.currentState !== "DONE"
              ? trans("CURRENTLY_REFRESHING_BUILD")
              : trans("REFRESHING_BUILD_DONE")}
          </h3>
        </div>
      );
    }

    return (
      <SlideDialog
        hasCloseButton={false}
        closeOnEscape
        title={trans("REFRESH_BUILD")}
      >
        <p>{trans("REFRESH_BUILD_NOTE")}</p>
        {progress}
        <div className="actions">
          <button
            type="submit"
            className="btn btn-primary"
            disabled={!this.isSafeToNavigate()}
            onClick={this.onRefresh.bind(this)}
          >
            {trans("REFRESH_BUILD")}
          </button>
          <button
            type="submit"
            className="btn btn-default"
            disabled={!this.isSafeToNavigate()}
            onClick={this.onCancel.bind(this)}
          >
            {trans(this.state.currentState === "DONE" ? "CLOSE" : "CANCEL")}
          </button>
        </div>
      </SlideDialog>
    );
  }
}
