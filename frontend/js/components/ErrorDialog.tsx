import React, { useCallback, useState } from "react";
import SlideDialog from "./SlideDialog";
import { trans, TranslationEntry } from "../i18n";
import { useLektorEvent } from "../events";

/**
 * Listen to events and show an error dialog (potentially on top of an open
 * dialog).
 */
export default function ErrorDialog(): JSX.Element | null {
  const [error, setError] = useState<{ code: string } | null>(null);

  const dismiss = useCallback(() => setError(null), []);

  useLektorEvent(
    "lektor-error",
    useCallback(({ detail }) => {
      setError(detail);
    }, [])
  );

  if (!error) {
    return null;
  }
  return (
    <SlideDialog
      dismiss={dismiss}
      hasCloseButton={false}
      title={trans("ERROR")}
    >
      <p>
        {trans("ERROR_OCURRED")}
        {": "}
        {trans(("ERROR_" + error.code) as TranslationEntry)}
      </p>
      <p>
        <button type="button" className="btn btn-primary" onClick={dismiss}>
          {trans("CLOSE")}
        </button>
      </p>
    </SlideDialog>
  );
}
