import React, { ChangeEvent, createRef, RefObject } from "react";

import SlideDialog from "../components/SlideDialog";
import { getApiUrl } from "../utils";
import { loadData } from "../fetch";
import { trans, trans_fallback } from "../i18n";
import { bringUpDialog } from "../richPromise";
import { RecordProps } from "../components/RecordComponent";

interface Server {
  id: string;
  short_target: string;
  name: string;
  name_i18n: Partial<Record<string, string>>;
}

/**
 * Render a <select for the available target servers.
 */
function TargetServers({
  activeTarget,
  servers,
  setActiveTarget,
}: {
  activeTarget: string;
  servers: Server[];
  setActiveTarget: (value: string) => void;
}) {
  function onChange(event: ChangeEvent<HTMLSelectElement>) {
    setActiveTarget(event.target.value);
  }
  const serverOptions = servers.map((server) => (
    <option value={server.id} key={server.id}>
      {trans_fallback(server.name_i18n, server.name) +
        " (" +
        server.short_target +
        ")"}
    </option>
  ));

  return (
    <dl>
      <dt>{trans("PUBLISH_SERVER")}</dt>
      <dd>
        <div className="input-group">
          <select
            value={activeTarget}
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

interface PublishState {
  servers: Server[];
  activeTarget: string;
  log: string[];
  currentState: "IDLE" | "BUILDING" | "PUBLISH" | "DONE";
}

type Props = RecordProps & { dismiss: () => void };

class Publish extends React.Component<Props, PublishState> {
  buildLog: RefObject<HTMLPreElement>;

  constructor(props: Props) {
    super(props);

    this.state = {
      servers: [],
      activeTarget: "",
      log: [],
      currentState: "IDLE",
    };

    this.buildLog = createRef();

    this.setActiveTarget = this.setActiveTarget.bind(this);
    this.onPublish = this.onPublish.bind(this);
  }

  componentDidMount() {
    this.syncDialog();
  }

  componentDidUpdate(prevProps: Props) {
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
    loadData("/servers", null).then(({ servers }) => {
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

  _beginBuild() {
    this.setState({
      log: [],
      currentState: "BUILDING",
    });
    loadData("/build", null, { method: "POST" }).then(() => {
      this._beginPublish();
    }, bringUpDialog);
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
        this.setState((state) => ({
          log: state.log.concat(data.msg),
        }));
      }
    });
  }

  setActiveTarget(activeTarget: string) {
    this.setState({ activeTarget });
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
        dismiss={this.props.dismiss}
        hasCloseButton={false}
        title={trans("PUBLISH")}
      >
        <p>{trans("PUBLISH_NOTE")}</p>
        <TargetServers
          activeTarget={this.state.activeTarget}
          servers={this.state.servers}
          setActiveTarget={this.setActiveTarget}
        />
        <p>
          <button
            type="submit"
            className="btn btn-primary"
            disabled={!this.isSafeToPublish()}
            onClick={this.onPublish}
          >
            {trans("PUBLISH")}
          </button>{" "}
          <button
            type="submit"
            className="btn btn-secondary border"
            disabled={!this.isSafeToPublish()}
            onClick={this.props.dismiss}
          >
            {trans(this.state.currentState === "DONE" ? "CLOSE" : "CANCEL")}
          </button>
        </p>
        {progress}
      </SlideDialog>
    );
  }
}

export default Publish;
