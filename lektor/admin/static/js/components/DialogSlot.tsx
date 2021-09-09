import React, { useCallback, useEffect, useState } from "react";
import FindFiles from "../dialogs/find-files/FindFiles";
import Publish from "../dialogs/Publish";
import Refresh from "../dialogs/Refresh";
import { LektorEvents, subscribe, unsubscribe } from "../events";
import { RecordProps } from "./RecordComponent";

type DialogDetails = LektorEvents["lektor-dialog"];

type DialogState = (DialogDetails & { preventNavigation?: boolean }) | null;

export default function DialogSlot(props: RecordProps) {
  const [dialog, setDialog] = useState<DialogState>(null);

  const dismiss = useCallback(
    () => setDialog((c) => (c?.preventNavigation ? c : null)),
    []
  );
  const prevent = useCallback(
    (preventNavigation: boolean) =>
      setDialog((d) => (d ? { ...d, preventNavigation } : null)),
    []
  );
  useEffect(() => {
    const handler = ({ detail }: CustomEvent<DialogDetails>) => {
      // Only change dialog if there is no dialog yet.
      setDialog((current) => current ?? detail);
    };
    subscribe("lektor-dialog", handler);
    return () => unsubscribe("lektor-dialog", handler);
  }, []);

  if (!dialog) {
    return null;
  }
  let el: JSX.Element | null = null;
  if (dialog.type === "find-files") {
    el = <FindFiles {...props} dismiss={dismiss} />;
  } else if (dialog.type === "refresh") {
    el = <Refresh dismiss={dismiss} preventNavigation={prevent} />;
  } else if (dialog.type === "publish") {
    el = (
      <Publish
        record={props.record}
        dismiss={dismiss}
        preventNavigation={prevent}
      />
    );
  }
  return (
    <div className="dialog-slot">
      {el}
      <div className="interface-protector" />
    </div>
  );
}
