import React from "react";
import { loadData } from "../utils";
import { trans } from "../i18n";

class ServerStatus extends React.Component {
  constructor(props) {
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

export default ServerStatus;
