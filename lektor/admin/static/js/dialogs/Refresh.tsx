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
    this.state = { currentState: "IDLE" };
    this.onRefresh = this.onRefresh.bind(this);
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
    this.setState({ currentState: "CLEANING" });
    loadData("/clean", null, { method: "POST" }).then(() => {
      this.setState({ currentState: "DONE" });
    }, bringUpDialog);
  }

  render() {
    return (
      <SlideDialog
        dismiss={this.props.dismiss}
        hasCloseButton={false}
        title={trans("REFRESH_BUILD")}
      >
        <p>{trans("REFRESH_BUILD_NOTE")}</p>
        {this.state.currentState !== "IDLE" && (
          <div>
            <h3>
              {this.state.currentState !== "DONE"
                ? trans("CURRENTLY_REFRESHING_BUILD")
                : trans("REFRESHING_BUILD_DONE")}
            </h3>
          </div>
        )}
        <p>
          <button
            type="submit"
            className="btn btn-primary"
            disabled={!this.isSafeToNavigate()}
            onClick={this.onRefresh}
          >
            {trans("REFRESH_BUILD")}
          </button>{" "}
          <button
            type="submit"
            className="btn btn-secondary border"
            disabled={!this.isSafeToNavigate()}
            onClick={this.props.dismiss}
          >
            {trans(this.state.currentState === "DONE" ? "CLOSE" : "CANCEL")}
          </button>
        </p>
      </SlideDialog>
    );
  }
}
