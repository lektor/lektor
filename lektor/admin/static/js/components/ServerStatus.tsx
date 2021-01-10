import React from "react";
import { loadData } from "../fetch";
import { trans } from "../i18n";

type State = { serverIsUp: boolean; projectId: string | null };

export default class ServerStatus extends React.Component<unknown, State> {
  intervalId: number | null;

  constructor(props: unknown) {
    super(props);
    this.state = {
      serverIsUp: true,
      projectId: null,
    };

    this.intervalId = null;
    this.onInterval = this.onInterval.bind(this);
  }

  componentDidMount() {
    this.intervalId = window.setInterval(this.onInterval, 2000);
  }

  componentWillUnmount() {
    if (this.intervalId !== null) {
      window.clearInterval(this.intervalId);
      this.intervalId = null;
    }
  }

  onInterval() {
    loadData("/ping", {}).then(
      (resp) => {
        if (this.state.projectId === null) {
          this.setState({
            projectId: resp.project_id,
          });
        }
        this.setState((state) => ({
          serverIsUp: state.projectId === resp.project_id,
        }));
      },
      () => {
        this.setState({
          serverIsUp: false,
        });
      }
    );
  }

  render() {
    if (this.state.serverIsUp) {
      return null;
    }
    return (
      <div className="server-down-panel">
        <div className="server-down-dialog">
          <h3>{trans("ERROR_SERVER_UNAVAILABLE")}</h3>
          <p>{trans("ERROR_SERVER_UNAVAILABLE_MESSAGE")}</p>
        </div>
      </div>
    );
  }
}
