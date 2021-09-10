import React, { useCallback, useEffect, useState } from "react";
import SlideDialog from "../components/SlideDialog";
import { loadData } from "../fetch";
import { trans } from "../i18n";
import { showErrorDialog } from "../error-dialog";

export default function Refresh({
  dismiss,
  preventNavigation,
}: {
  dismiss: () => void;
  preventNavigation: (v: boolean) => void;
}) {
  const [state, setState] = useState<"IDLE" | "DONE" | "CLEANING">("IDLE");
  const isSafeToNavigate = state === "IDLE" || state === "DONE";

  const refresh = useCallback(() => {
    setState("CLEANING");
    loadData("/clean", null, { method: "POST" }).then(() => {
      setState("DONE");
    }, showErrorDialog);
  }, []);
  useEffect(
    () => preventNavigation(!isSafeToNavigate),
    [preventNavigation, isSafeToNavigate]
  );

  return (
    <SlideDialog
      dismiss={dismiss}
      hasCloseButton={false}
      title={trans("REFRESH_BUILD")}
    >
      <p>{trans("REFRESH_BUILD_NOTE")}</p>
      <p>
        <button
          type="button"
          className="btn btn-primary"
          disabled={!isSafeToNavigate}
          onClick={refresh}
        >
          {trans("REFRESH_BUILD")}
        </button>{" "}
        <button
          type="button"
          className="btn btn-secondary border"
          disabled={!isSafeToNavigate}
          onClick={dismiss}
        >
          {trans(state === "DONE" ? "CLOSE" : "CANCEL")}
        </button>
      </p>
      {state !== "IDLE" && (
        <div>
          <h3>
            {state !== "DONE"
              ? trans("CURRENTLY_REFRESHING_BUILD")
              : trans("REFRESHING_BUILD_DONE")}
          </h3>
        </div>
      )}
    </SlideDialog>
  );
}
