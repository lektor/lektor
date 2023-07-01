import React, {
  ChangeEvent,
  MouseEvent,
  RefObject,
  useEffect,
  useReducer,
  useRef,
} from "react";
import { trans, TranslationEntry } from "../i18n";
import { getInputClass, WidgetProps } from "./types";

const config = {
  // On initial render, if the natural height of the textarea is less than
  // than maxInitialHeight, the textarea will start in autosize mode.
  // Otherwise, it will start with a static height of defaultStaticHeight.
  // (Both of these are relative to windowHeight.)
  maxInitialHeight: 0.6,
  defaultStaticHeight: 0.4,

  // The maximum target height for the "shrink" button, relative to windowHeight.
  maxTargetHeight: 0.8,
  // The minimum target height for the "shrink" button, in lines.
  minTargetLines: 5,
  // Default shrink factor, if remembered height is not viable
  fallbackShrinkFactor: 0.5,

  // When textarea is manually resized, if the new size larger than the
  // largest of (extraLines * lineHeight) or (maxResizeHeight * windowHeight),
  // the textarea will be switched to autosize mode.
  extraLines: 2,
  maxResizeHeight: 0.8,

  // When window is narrower than this, textareas are always autosized
  minWindowWidth: 576,
} as const;

function _pixels(dimension: string): number {
  return Number(dimension.replace(/px/, ""));
}

function deref<T>(ref: RefObject<T>): T {
  if (ref.current === undefined || ref.current === null) {
    throw new Error("Attempt to dereference undefined reference");
  }
  return ref.current;
}

/**
 * Determine whether we are running on a touch device.
 *
 * @return True if we are on a touch device
 */
function isTouchDevice(): boolean {
  return "ontouchstart" in window || navigator.maxTouchPoints > 0;
}

/**
 * Determine whether to enable manual resizing of textareas via drag-handle.
 *
 * Since nested scrollbars on touch devices seem horrible,
 * on touch and small devices we will disable manual resizeability.
 * (In that case textareas are always autosized to fit all of their content.)
 *
 * @return Whether to enable resizing via drag-handle
 */
function shouldEnableDragHandle(): boolean {
  return window.innerWidth >= config.minWindowWidth && !isTouchDevice();
}

type TextAreaResizedEvent = CustomEvent<{ height: number }>;

declare global {
  interface HTMLElementEventMap {
    "textarea-resized": TextAreaResizedEvent;
  }
}

/**
 * Arrange to send custom "textarea-resized" event to textarea
 * when it is resized by the user (presumably by using the drag-handle.)
 *
 * @param  textarea The textarea to watch.
 *
 * @return Callback to disconnect instrumentation.
 */
function textareaResizeWatcher(textarea: HTMLTextAreaElement): () => void {
  let height: string;

  function mousedownListener() {
    height = textarea.style.height;
    window.addEventListener("mouseup", mouseupListener, { once: true });
  }

  function mouseupListener() {
    if (textarea.style.height !== height) {
      // height changed, presumably via drag-handle
      const event: TextAreaResizedEvent = new CustomEvent("textarea-resized", {
        detail: { height: _pixels(textarea.style.height) },
      });
      textarea.dispatchEvent(event);
    }
  }

  textarea.addEventListener("mousedown", mousedownListener);

  return () => {
    window.removeEventListener("mouseup", mouseupListener);
    textarea.removeEventListener("mousedown", mousedownListener);
  };
}

// Widget state
interface State {
  autosized: boolean;
  height: number;
  resizeable: boolean;

  lineHeight: number;
  borderHeight: number;
  decorationHeight: number; // border + padding height
}

type ResizeAction =
  | { type: "autosize" } // Autosize textarea
  | {
      type: "set-height"; // Set textarea to specific height
      height: number;
    };

type Action =
  | ResizeAction
  | ({ type: "initialize" } & InitStateArg)
  | { type: "enable-drag-handle" | "disable-drag-handle" };

interface InitStateArg {
  textarea: HTMLTextAreaElement;
  replica: HTMLElement;
}

function initState(arg: null | InitStateArg) {
  const resizeable = shouldEnableDragHandle();
  const height = window.innerHeight * config.defaultStaticHeight;
  let autosized = true;
  let lineHeight = 21,
    borderHeight = 2,
    decorationHeight = 12.5;

  if (arg) {
    const { textarea, replica } = arg;
    const cs = getComputedStyle(textarea);

    lineHeight = _pixels(cs.lineHeight);
    borderHeight = _pixels(cs.borderTopWidth) + _pixels(cs.borderBottomWidth);
    decorationHeight =
      borderHeight + _pixels(cs.paddingTop) + _pixels(cs.paddingBottom);

    if (resizeable) {
      const naturalHeight = replica.scrollHeight + borderHeight;
      if (naturalHeight > window.innerHeight * config.maxInitialHeight) {
        autosized = false;
      }
    }
  }

  return {
    resizeable,
    autosized,
    height,
    lineHeight,
    borderHeight,
    decorationHeight,
  };
}

function reduceState(state: Readonly<State>, action: Action): State {
  switch (action.type) {
    case "initialize": {
      // The real initial state can only be computed after the first render
      return initState(action);
    }

    case "set-height":
      // Set textarea to statically sized
      if (!state.autosized) return state;
      return { ...state, autosized: false, height: action.height };

    case "autosize":
      // Set textarea to autosize
      if (state.autosized) return state;
      return { ...state, autosized: true };

    case "enable-drag-handle":
      if (state.resizeable) return state;
      return { ...state, resizeable: true };

    case "disable-drag-handle":
      if (!state.resizeable) return state;
      return { ...state, resizeable: false, autosized: true };
  }
}

export function MultiLineTextInputWidget({
  type,
  value,
  placeholder,
  disabled,
  onChange: onChangeProp,
}: WidgetProps) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const replicaRef = useRef<HTMLDivElement>(null);

  const [state, dispatch] = useReducer(reduceState, null, initState);

  useEffect(() => {
    // Initial render
    const textarea = deref(textareaRef);
    const replica = deref(replicaRef);

    // Initialize state
    dispatch({ type: "initialize", textarea, replica });

    const windowResizeListener = () => {
      if (shouldEnableDragHandle()) {
        dispatch({ type: "enable-drag-handle" });
      } else {
        dispatch({ type: "disable-drag-handle" });
      }
    };
    window.addEventListener("resize", windowResizeListener);

    // Arrange to deliver custom "textarea-resized" event when drag-handled
    const disconnectResizeWatcher = textareaResizeWatcher(textarea);

    return () => {
      disconnectResizeWatcher();
      window.removeEventListener("resize", windowResizeListener);
    };
  }, []);

  useEffect(() => {
    if (state.resizeable) {
      const textarea = deref(textareaRef);
      const replica = deref(replicaRef);

      // Adjust replica max-height to allow widget to shrink when textarea is drag-handled
      const observer = new MutationObserver(() => {
        if (textarea.style.height) {
          replica.style.maxHeight = "0px";
        }
      });
      observer.observe(textarea, { attributeFilter: ["style"] });

      // Watch for manual resizing via drag-handle
      const resizeListener = (event: TextAreaResizedEvent) => {
        const { height } = event.detail;
        dispatch({ type: "set-height", height });
      };
      textarea.addEventListener("textarea-resized", resizeListener);

      return () => {
        textarea.removeEventListener("textarea-resized", resizeListener);
        observer.disconnect();
      };
    }
  }, [state.resizeable]);

  const getNaturalHeight = () => {
    const replica = replicaRef.current;
    if (replica) {
      // Sync replica content, since React may not have done so yet
      replica.innerText = value;
      return replica.scrollHeight + state.borderHeight;
    } else {
      return 0;
    }
  };

  useEffect(() => {
    if (!state.autosized) {
      // If statically sized to ridiculously large size, reset to autosized
      const reasonableHeight = Math.max(
        getNaturalHeight() + state.lineHeight * config.extraLines,
        window.innerHeight * config.maxResizeHeight,
      );
      if (state.height > reasonableHeight) {
        dispatch({ type: "autosize" });
      }
    }
  });

  const onChange = (event: ChangeEvent<HTMLTextAreaElement>) => {
    onChangeProp(event.target.value);
  };

  /* How the textarea autosizing works
   *
   * The idea is ripped off from here:
   *
   *   https://css-tricks.com/the-cleanest-trick-for-autogrowing-textareas/
   *
   * We stack an (invisible) <div> under our <textarea> in a container
   * with display: grid.
   *
   * The issue we are trying to solve is that <textarea>s do not expand
   * when content is added to them.  However, <div>s do!
   *
   * The contents of the <textarea> is duplicated to the <div>. The
   * grid layout ensures that when the <div> expands, the <textarea> is
   * expanded to match.
   */
  return (
    <div className="text-widget">
      <div
        style={{ maxHeight: state.autosized ? "" : "0px" }}
        ref={replicaRef}
        className="text-widget__replica"
      >
        {value}
      </div>
      <textarea
        style={{ height: state.autosized ? "" : `${state.height}px` }}
        ref={textareaRef}
        className={[
          "text-widget__textarea",
          state.autosized && "text-widget__textarea--autosized",
          state.resizeable && "text-widget__textarea--resizeable",
          getInputClass(type),
        ]
          .filter(Boolean)
          .join(" ")}
        onChange={onChange}
        value={value}
        disabled={disabled}
        placeholder={placeholder}
      />
      <ToggleButton
        state={state}
        dispatch={dispatch}
        naturalHeight={getNaturalHeight()}
      />
    </div>
  );
}

function ToggleButton({
  state,
  dispatch,
  naturalHeight,
}: {
  state: Readonly<State>;
  dispatch: (action: Action) => void;
  naturalHeight: number;
}) {
  const action = getToggleAction(state, naturalHeight);

  if (!action) return null;

  const { title, icon } = toggleButtonLabels[action.type];

  const onClick = (event: MouseEvent<HTMLAnchorElement>) => {
    event.preventDefault();
    dispatch(action);
  };

  const className =
    "position-absolute top-0 start-100 translate-middle bg-light border rounded-circle";

  return (
    <a href="#" title={trans(title)} onClick={onClick} className={className}>
      <i className={`fa fa-${icon} fa-fw`} />
    </a>
  );
}

interface ToggleButtonLabel {
  title: TranslationEntry;
  icon: string;
}

const toggleButtonLabels: Record<string, Readonly<ToggleButtonLabel>> = {
  autosize: {
    title: "AUTOSIZE_TEXTAREA",
    icon: "expand",
  },
  "set-height": {
    title: "SHRINK_TEXTAREA",
    icon: "compress",
  },
} as const;

// Compute action to be dispatched by toggle button
function getToggleAction(
  state: Readonly<State>,
  naturalHeight: number, // Natural height of textarea
): ResizeAction | null {
  // Deduce height to size textarea to if "shrink" button is clicked
  if (!state.resizeable) {
    return null;
  }
  if (!state.autosized) {
    return { type: "autosize" };
  }

  const targetHeight = Math.min(
    state.height, // last manually set height
    Math.ceil(window.innerHeight * config.maxTargetHeight),
  );
  if (targetHeight < naturalHeight) {
    return { type: "set-height", height: targetHeight };
  }

  // Can't shrink if target height is bigger than natural height
  // See if we can find a smaller targetHeight
  const lines = Math.round(
    (naturalHeight - state.decorationHeight) / state.lineHeight,
  );
  const targetLines = Math.max(
    config.minTargetLines,
    Math.ceil(lines * config.fallbackShrinkFactor),
  );
  const fallbackHeight = Math.ceil(
    targetLines * state.lineHeight + state.decorationHeight,
  );
  if (fallbackHeight < naturalHeight) {
    return { type: "set-height", height: fallbackHeight };
  }

  return null;
}
