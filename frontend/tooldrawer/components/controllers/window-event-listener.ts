import { ReactiveController, ReactiveControllerHost } from "lit";

type EventListener = (event: Event) => void;

/*
 * Controller to manage window event listeners
 */
export class WindowEventListenerController implements ReactiveController {
  private host: ReactiveControllerHost;
  private options: AddEventListenerOptions;

  constructor(host: ReactiveControllerHost, options?: AddEventListenerOptions) {
    this.host = host;
    this.options = options ?? {};
    host.addController(this);
  }

  hostConnected() {
    for (const [eventType] of this._windowEventListeners) {
      window.addEventListener(eventType, this._listener, this.options);
    }
    this._connected = true;
  }

  hostDisconnected() {
    this._removeHandlers();
    this._connected = false;
  }

  private _connected = false;
  private _windowEventListeners = new Map<string, EventListener[]>();

  add<ET extends keyof WindowEventMap>(
    eventType: ET,
    listener: (event: WindowEventMap[ET]) => void,
  ) {
    const listeners = this._windowEventListeners.get(eventType);
    if (listeners) {
      listeners.push(listener as EventListener);
    } else {
      if (this._connected) {
        window.addEventListener(eventType, this._listener, this.options);
      }
      this._windowEventListeners.set(eventType, [listener as EventListener]);
    }
  }

  clear() {
    this._removeHandlers();
    this._windowEventListeners.clear();
  }

  private _removeHandlers() {
    for (const [eventType] of this._windowEventListeners) {
      window.removeEventListener(eventType, this._listener, this.options);
    }
  }

  private _listener = (event: Event) => {
    this._windowEventListeners
      .get(event.type)
      ?.map((listener) => listener.call(this.host, event));
  };
}

export default WindowEventListenerController;
