/* eslint-env browser */

import React, { createRef } from "react";

import SlideDialog from "../components/SlideDialog";
import { apiRequest, loadData, getApiUrl } from "../utils";
import { trans } from "../i18n";
import dialogSystem from "../dialogSystem";
import makeRichPromise, { bringUpDialog } from "../richPromise";

/**
 * Render a <select for the available target servers.
 */
function TargetServers({ activeTarget, servers, setActiveTarget }) {
  function onChange(event) {
    setActiveTarget(event.target.value);
  }
  const serverOptions = servers.map((server) => (
    <option value={server.id} key={server.id}>
      {trans(server.name_i18n) + " (" + server.short_target + ")"}
    </option>
  ));

  return (
    <dl>
      <dt>{trans("PUBLISH_SERVER")}</dt>
      <dd>
        <div className="input-group">
          <select
            value={activeTarget || ""}
            onChange={onChange}
            className="form-control"
          >
            {serverOptions}
          </select>
        </div>
      </dd>
    </dl>
  );
}

class Publish extends React.Component {
  constructor(props) {
    super(props);

    this.state = {
      servers: [],
      activeTarget: null,
      log: [],
      currentState: "IDLE",
    };

    this.buildLog = createRef();
    this.setActiveTarget = this.setActiveTarget.bind(this);
  }

  componentDidMount() {
    this.syncDialog();
  }

  componentDidUpdate(prevProps) {
    if (prevProps.match.params.path !== this.props.match.params.path) {
      this.syncDialog();
    }
    const node = this.buildLog.current;
    if (node) {
      node.scrollTop = node.scrollHeight;
    }
  }

  preventNavigation() {
    return !this.isSafeToPublish();
  }

  syncDialog() {
    loadData("/servers", {}).then(({ servers }) => {
      this.setState({
        servers: servers,
        activeTarget: servers && servers.length ? servers[0].id : null,
      });
    }, bringUpDialog);
  }

  isSafeToPublish() {
    return (
      this.state.currentState === "IDLE" || this.state.currentState === "DONE"
    );
  }

  onPublish() {
    if (this.isSafeToPublish()) {
      this._beginBuild();
    }
  }

  onCancel() {
    dialogSystem.dismissDialog();
  }

  _beginBuild() {
    this.setState({
      log: [],
      currentState: "BUILDING",
    });
    apiRequest(
      "/build",
      {
        method: "POST",
      },
      makeRichPromise
    ).then((resp) => {
      this._beginPublish();
    });
  }

  _beginPublish() {
    this.setState({
      currentState: "PUBLISH",
    });

    const es = new EventSource(
      getApiUrl("/publish") +
        "?server=" +
        encodeURIComponent(this.state.activeTarget)
    );
    es.addEventListener("message", (event) => {
      const data = JSON.parse(event.data);
      if (data === null) {
        this.setState({
          currentState: "DONE",
        });
        es.close();
      } else {
        this.setState({
          log: this.state.log.concat(data.msg),
        });
      }
    });
  }

  setActiveTarget(activeTarget) {
    this.setState({ activeTarget: activeTarget });
  }

  render() {
    const progress =
      this.state.currentState !== "IDLE" ? (
        <div>
          <h3>
            {this.state.currentState !== "DONE"
              ? trans("CURRENTLY_PUBLISHING")
              : trans("PUBLISH_DONE")}
          </h3>
          <pre>
            {trans("STATE") +
              ": " +
              trans("PUBLISH_STATE_" + this.state.currentState)}
          </pre>
          <pre ref={this.buildLog} className="build-log">
            {this.state.log.join("\n")}
          </pre>
        </div>
      ) : null;

    return (
      <SlideDialog
        hasCloseButton={false}
        closeOnEscape
        title={trans("PUBLISH")}
      >
        <p>{trans("PUBLISH_NOTE")}</p>
        <TargetServers
          activeTarget={this.state.activeTarget}
          servers={this.state.servers}
          setActiveTarget={this.setActiveTarget}
        />
        <div className="actions">
          <button
            type="submit"
            className="btn btn-primary"
            disabled={!this.isSafeToPublish()}
            onClick={this.onPublish.bind(this)}
          >
            {trans("PUBLISH")}
          </button>
          <button
            type="submit"
            className="btn btn-default"
            disabled={!this.isSafeToPublish()}
            onClick={this.onCancel.bind(this)}
          >
            {trans(this.state.currentState === "DONE" ? "CLOSE" : "CANCEL")}
          </button>
        </div>
        {progress}
      </SlideDialog>
    );
  }
}

export default Publish;
