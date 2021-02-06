import React from "react";
import SlideDialog from "../components/SlideDialog";
import { loadData } from "../fetch";
import { trans } from "../i18n";
import { bringUpDialog } from "../richPromise";

type RefreshState = "IDLE" | "DONE" | "CLEANING";
type Props = { dismiss: () => void };

export default class Refresh extends React.Component<
  Props,
  { currentState: RefreshState }
> {
  constructor(props: Props) {
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
        dismiss={this.props.dismiss}
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
            onClick={this.props.dismiss}
          >
            {trans(this.state.currentState === "DONE" ? "CLOSE" : "CANCEL")}
          </button>
        </div>
      </SlideDialog>
    );
  }
}
