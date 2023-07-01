import { useCallback, useEffect, useReducer, useRef } from "react";
import { flushSync } from "react-dom";

interface State {
  changes: number;
  flushed: number;
}

function reducer(state: State, flushed: number | null): State {
  if (flushed !== null) {
    return { ...state, flushed: flushed };
  } else {
    return { ...state, changes: state.changes + 1 };
  }
}

type SetCleanFunction<T> = (
  cb: () => T | Promise<T>,
  options?: { sync: boolean }
) => Promise<T>;

/**
 * An async-safe "pending changes" flag.
 *
 * This addresses the situation where a form is used to update data on a server.
 *
 * When any form field is edited, the form is immediately dirty.  However, when we
 * save the form, we do not mark the form "clean" until the remote request completes.
 *
 * But what if the form was further edited while the "save" request was in-flight?
 * It is incorrect to simply mark the form clean when the "save" completes, since
 * the data in the form still does not agree with what's been saved to the server.
 *
 * Usage:
 *
 * const [isDirty, setDirty, setClean] = useChangedFlag();
 *
 * // to set the dirty flag, call setDirty()
 * const changeHandler = useCallback(() => setDirty(), [setDirty]);
 *
 * // to clear the dirty flag, pass the save function to setClean
 * const saveHandler = useCallback(() => setClean(() => saveMyData));
 *
 * When setClean will call the callback (saveMyData). When the callback completes,
 * it will set the "current" count to what the value of the changed count was
 * at the beginning of the call.  As a result, if setDirty() was called sometime
 * during the execution of the callback, the dirty flag will still be set.
 *
 * If setClean is passed a second options argument of { sync: true }, the call to
 * update the flag state will be wrapped in a call to ReactDOM.flushSync to ensure
 * the state update is rendered immediately.
 */
export function useChangedFlag<T>(): [
  boolean,
  () => void,
  SetCleanFunction<T>
] {
  const [state, setFlushed] = useReducer(reducer, { changes: 0, flushed: 0 });
  const changesRef = useRef(state.changes);

  useEffect(() => {
    changesRef.current = state.changes;
  }, [state]);

  const hasPendingChanges = state.changes != state.flushed;

  const setDirty = useCallback(() => {
    setFlushed(null);
  }, [setFlushed]);
  const setClean = useCallback(
    async (cb: () => T | Promise<T>, options?: { sync: boolean }) => {
      const changes = changesRef.current;
      const update = () => setFlushed(changes);

      const result = await cb();
      options?.sync ? flushSync(update) : update();
      return result;
    },
    [setFlushed]
  );

  return [hasPendingChanges, setDirty, setClean];
}
