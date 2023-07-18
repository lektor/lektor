import React, { useCallback, useState, Dispatch, SetStateAction } from "react";
import SlideDialog from "../components/SlideDialog";
import { trans } from "../i18n";
import {
  eraseHotkeyKeys,
  getShortcutKey,
  ShortcutAction,
  ShortcutKey,
  ShortcutKeyMap,
} from "../shortcut-keys";
import {
  defaultAppSettings,
  useAppSettings,
  AppSettings,
} from "../context/appsettings-context";

export default function Preferences({
  setAppSettings,
  dismiss,
}: {
  setAppSettings: Dispatch<SetStateAction<AppSettings>>;
  dismiss: () => void;
}): JSX.Element {
  const appSettings = useAppSettings();
  const [state, setState] = useState(appSettings);

  const save = () => {
    setAppSettings(state);
    dismiss();
  };

  const setKeyMap = useCallback((action: SetStateAction<ShortcutKeyMap>) => {
    setState((state) => ({
      ...state,
      shortcutKeyMap:
        typeof action === "function" ? action(state.shortcutKeyMap) : action,
    }));
  }, []);

  return (
    <SlideDialog
      dismiss={dismiss}
      hasCloseButton={false}
      title={trans("PREFERENCES")}
    >
      <form>
        <ShortcutKeyPrefs keyMap={state.shortcutKeyMap} setKeyMap={setKeyMap} />
        <div className="d-flex">
          <button
            type="submit"
            disabled={state === appSettings}
            className="btn btn-primary border me-2"
            onClick={save}
          >
            {trans("SAVE_CHANGES")}
          </button>
          <button
            type="button"
            className="btn btn-secondary border me-2"
            disabled={state === defaultAppSettings}
            onClick={() => {
              setState(defaultAppSettings);
            }}
          >
            {trans("RESET_TO_DEFAULTS")}
          </button>
          <button
            type="button"
            className="btn btn-secondary border"
            onClick={dismiss}
          >
            {trans("CANCEL")}
          </button>
        </div>
      </form>
    </SlideDialog>
  );
}

function ShortcutKeyPrefs({
  keyMap,
  setKeyMap,
}: {
  keyMap: ShortcutKeyMap;
  setKeyMap: Dispatch<SetStateAction<ShortcutKeyMap>>;
}): JSX.Element {
  const setShortcut = useCallback(
    (action: ShortcutAction, key: ShortcutKey | null) => {
      setKeyMap(
        (keyMap) =>
          new Map(
            Array.from(keyMap.entries(), ([a, k]) => [
              a,
              a === action ? key : k !== key ? k : null,
            ]),
          ),
      );
    },
    [setKeyMap],
  );

  return (
    <fieldset className="border border-dark p-2 mb-3">
      <legend>Shortcut Keys</legend>
      {Array.from(keyMap, ([action, key]) => (
        <div className="row mb-3" key={action}>
          <label htmlFor={action} className="col-sm-6 col-form-label text-end">
            {trans(action)}
          </label>
          <div className="col-sm-4">
            <ShortcutKeyInputWidget
              value={key}
              onValueChange={(key) => {
                setShortcut(action, key);
              }}
              className="form-control"
              id={action}
            />
          </div>
        </div>
      ))}
    </fieldset>
  );
}

function ShortcutKeyInputWidget({
  value,
  onValueChange,
  ...props
}: Omit<
  JSX.IntrinsicElements["input"],
  "value" | "type" | "onChange" | "onKeyDown"
> & {
  value: ShortcutKey | null;
  onValueChange: Dispatch<ShortcutKey | null>;
}): JSX.Element {
  return (
    <input
      type="text"
      value={value ?? ""}
      onChange={() => null /* prevent warning from React Developer Tools */}
      onKeyDown={(event) => {
        const key = getShortcutKey(event);
        const doUnset = eraseHotkeyKeys.has(event.key);
        if (key || doUnset) {
          event.preventDefault();
          event.stopPropagation();
          onValueChange(key);
        }
      }}
      {...props}
    />
  );
}
