/* eslint-env browser */

import React, { createRef } from "react";

import SlideDialog from "../components/SlideDialog";
import { apiRequest, loadData, getApiUrl } from "../utils";
import i18n from "../i18n";
import dialogSystem from "../dialogSystem";
import makeRichPromise from "../richPromise";

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
    loadData("/servers", {}, makeRichPromise).then(({ servers }) => {
      this.setState({
        servers: servers,
        activeTarget: servers && servers.length ? servers[0].id : null,
      });
    });
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

  onSelectServer(event) {
    this.setState({
      activeTarget: event.target.value,
    });
  }

  render() {
    const servers = this.state.servers.map((server) => {
      return (
        <option value={server.id} key={server.id}>
          {i18n.trans(server.name_i18n) + " (" + server.short_target + ")"}
        </option>
      );
    });

    let progress = null;
    if (this.state.currentState !== "IDLE") {
      progress = (
        <div>
          <h3>
            {this.state.currentState !== "DONE"
              ? i18n.trans("CURRENTLY_PUBLISHING")
              : i18n.trans("PUBLISH_DONE")}
          </h3>
          <pre>
            {i18n.trans("STATE") +
              ": " +
              i18n.trans("PUBLISH_STATE_" + this.state.currentState)}
          </pre>
          <pre ref={this.buildLog} className="build-log">
            {this.state.log.join("\n")}
          </pre>
        </div>
      );
    }

    return (
      <SlideDialog
        hasCloseButton={false}
        closeOnEscape
        title={i18n.trans("PUBLISH")}
      >
        <p>{i18n.trans("PUBLISH_NOTE")}</p>
        <dl>
          <dt>{i18n.trans("PUBLISH_SERVER")}</dt>
          <dd>
            <div className="input-group">
              <select
                value={this.state.activeTarget}
                onChange={this.onSelectServer.bind(this)}
                className="form-control"
              >
                {servers}
              </select>
            </div>
          </dd>
        </dl>
        <div className="actions">
          <button
            type="submit"
            className="btn btn-primary"
            disabled={!this.isSafeToPublish()}
            onClick={this.onPublish.bind(this)}
          >
            {i18n.trans("PUBLISH")}
          </button>
          <button
            type="submit"
            className="btn btn-default"
            disabled={!this.isSafeToPublish()}
            onClick={this.onCancel.bind(this)}
          >
            {i18n.trans(
              this.state.currentState === "DONE" ? "CLOSE" : "CANCEL"
            )}
          </button>
        </div>
        {progress}
      </SlideDialog>
    );
  }
}

export default Publish;
