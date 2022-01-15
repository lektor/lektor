import React, { useEffect, useState } from "react";
import { get } from "../fetch";
import { trans } from "../i18n";

type State = { serverIsUp: boolean; projectId: string | null };

export default function ServerStatus(): JSX.Element | null {
  const [state, setState] = useState<State>({
    serverIsUp: true,
    projectId: null,
  });

  useEffect(() => {
    const onInterval = () => {
      get("/ping", null).then(
        ({ project_id }) => {
          setState(({ projectId }) =>
            projectId === null
              ? { projectId: project_id, serverIsUp: true }
              : { projectId, serverIsUp: projectId === project_id }
          );
        },
        () => {
          setState((s) => ({ ...s, serverIsUp: false }));
        }
      );
    };
    const id = window.setInterval(onInterval, 2000);
    return () => window.clearInterval(id);
  }, []);

  if (state.serverIsUp) {
    return null;
  }
  return (
    <div className="interface-protector server-down-panel">
      <div className="server-down-dialog">
        <h3>{trans("ERROR_SERVER_UNAVAILABLE")}</h3>
        <p>{trans("ERROR_SERVER_UNAVAILABLE_MESSAGE")}</p>
      </div>
    </div>
  );
}
