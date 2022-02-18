import React, {
  ChangeEvent,
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";

import SlideDialog from "../components/SlideDialog";
import { apiUrl, get, post } from "../fetch";
import { trans, trans_fallback } from "../i18n";
import { showErrorDialog } from "../error-dialog";

export interface Server {
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

type PublishState = "IDLE" | "BUILDING" | "PUBLISH" | "DONE";

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

function Publish({
  dismiss,
  preventNavigation,
}: {
  dismiss: () => void;
  preventNavigation: (b: boolean) => void;
}): JSX.Element {
  const [servers, setServers] = useState<Server[]>([]);
  const [activeTarget, setActiveTarget] = useState("");
  const [log, setLog] = useState<string[]>([]);
  const [state, setState] = useState<PublishState>("IDLE");

  useEffect(() => {
    get("/servers", null).then(({ servers }) => {
      setServers(servers);
      setActiveTarget(servers.length ? servers[0].id : "");
    }, showErrorDialog);
  }, []);

  const onPublish = useCallback(() => {
    setLog([]);
    setState("BUILDING");
    preventNavigation(true);
    post("/build", null).then(() => {
      setState("PUBLISH");

      const eventSource = new EventSource(
        apiUrl("/publish", { server: activeTarget })
      );
      eventSource.addEventListener("message", (event) => {
        const data = JSON.parse(event.data);
        if (data === null) {
          setState("DONE");
          preventNavigation(false);
          eventSource.close();
        } else {
          setLog((log) => log.concat(data.msg));
        }
      });
    }, showErrorDialog);
  }, [activeTarget, preventNavigation]);
  const isSafeToPublish = state === "IDLE" || state === "DONE";

  return (
    <SlideDialog
      dismiss={dismiss}
      hasCloseButton={false}
      title={trans("PUBLISH")}
    >
      <p>{trans("PUBLISH_NOTE")}</p>
      <TargetServers
        activeTarget={activeTarget}
        servers={servers}
        setActiveTarget={setActiveTarget}
      />
      <p>
        <button
          type="button"
          className="btn btn-primary"
          disabled={!isSafeToPublish}
          onClick={onPublish}
        >
          {trans("PUBLISH")}
        </button>{" "}
        <button
          type="button"
          className="btn btn-secondary border"
          disabled={!isSafeToPublish}
          onClick={dismiss}
        >
          {trans(state === "DONE" ? "CLOSE" : "CANCEL")}
        </button>
      </p>
      {state !== "IDLE" ? (
        <>
          <h3>
            {state !== "DONE"
              ? trans("CURRENTLY_PUBLISHING")
              : trans("PUBLISH_DONE")}
          </h3>
          <pre>{trans("STATE") + ": " + trans(`PUBLISH_STATE_${state}`)}</pre>
          <BuildLog log={log} />
        </>
      ) : null}
    </SlideDialog>
  );
}

export default Publish;
