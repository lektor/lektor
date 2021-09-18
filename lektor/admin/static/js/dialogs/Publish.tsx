import React, { ChangeEvent, useEffect, useRef } from "react";

import SlideDialog from "../components/SlideDialog";
import { getApiUrl } from "../utils";
import { loadData } from "../fetch";
import { trans, trans_fallback } from "../i18n";
import { showErrorDialog } from "../error-dialog";
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

function BuildLog({ log }: { log: string[] }) {
  const buildLog = useRef<HTMLPreElement | null>(null);
  useEffect(() => {
    const node = buildLog.current;
    if (node) {
      node.scrollTop = node.scrollHeight;
    }
  }, [log]);
  return (
    <pre ref={buildLog} className="build-log">
      {log.join("\n")}
    </pre>
  );
}

type Props = Pick<RecordProps, "record"> & {
  dismiss: () => void;
  preventNavigation: (b: boolean) => void;
};

class Publish extends React.Component<Props, PublishState> {
  constructor(props: Props) {
    super(props);

    this.state = {
      servers: [],
      activeTarget: "",
      log: [],
      currentState: "IDLE",
    };

    this.setActiveTarget = this.setActiveTarget.bind(this);
    this.onPublish = this.onPublish.bind(this);
  }

  componentDidMount() {
    this.syncDialog();
  }

  syncDialog() {
    loadData("/servers", null).then(({ servers }: { servers: Server[] }) => {
      this.setState({
        servers,
        activeTarget: servers.length ? servers[0].id : "",
      });
    }, showErrorDialog);
  }

  onPublish() {
    this.setState({ log: [], currentState: "BUILDING" });
    this.props.preventNavigation(true);
    loadData("/build", null, { method: "POST" }).then(() => {
      this.setState({ currentState: "PUBLISH" });

      const es = new EventSource(
        getApiUrl("/publish") +
          "?server=" +
          encodeURIComponent(this.state.activeTarget)
      );
      es.addEventListener("message", (event) => {
        const data = JSON.parse(event.data);
        if (data === null) {
          this.setState({ currentState: "DONE" });
          this.props.preventNavigation(false);
          es.close();
        } else {
          this.setState((state) => ({
            log: state.log.concat(data.msg),
          }));
        }
      });
    }, showErrorDialog);
  }

  setActiveTarget(activeTarget: string) {
    this.setState({ activeTarget });
  }

  render() {
    const state = this.state.currentState;
    const isSafeToPublish = state === "IDLE" || state === "DONE";

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
            type="button"
            className="btn btn-primary"
            disabled={!isSafeToPublish}
            onClick={this.onPublish}
          >
            {trans("PUBLISH")}
          </button>{" "}
          <button
            type="button"
            className="btn btn-secondary border"
            disabled={!isSafeToPublish}
            onClick={this.props.dismiss}
          >
            {trans(state === "DONE" ? "CLOSE" : "CANCEL")}
          </button>
        </p>
        {state !== "IDLE" ? (
          <div>
            <h3>
              {state !== "DONE"
                ? trans("CURRENTLY_PUBLISHING")
                : trans("PUBLISH_DONE")}
            </h3>
            <pre>{trans("STATE") + ": " + trans(`PUBLISH_STATE_${state}`)}</pre>
            <BuildLog log={this.state.log} />
          </div>
        ) : null}
      </SlideDialog>
    );
  }
}

export default Publish;
