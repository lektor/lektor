import React, { useCallback, useEffect, useState } from "react";
import FindFiles from "../dialogs/find-files/FindFiles";
import Publish from "../dialogs/Publish";
import Refresh from "../dialogs/Refresh";
import { LektorEvents, subscribe, unsubscribe } from "../events";

type DialogDetails = LektorEvents["lektor-dialog"];

type DialogState = (DialogDetails & { preventNavigation?: boolean }) | null;

export default function DialogSlot(): JSX.Element | null {
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
  if (dialog.type === "find-files") {
    return <FindFiles dismiss={dismiss} />;
  } else if (dialog.type === "refresh") {
    return <Refresh dismiss={dismiss} preventNavigation={prevent} />;
  } else if (dialog.type === "publish") {
    return <Publish dismiss={dismiss} preventNavigation={prevent} />;
  }
  const exhaustiveCheck: never = dialog.type;
  throw new Error(exhaustiveCheck);
}
