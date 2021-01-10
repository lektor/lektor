import { LektorEvent } from "./events";

class Hub {
  _subscriptions: Map<string, Set<(e: any) => void>>;

  constructor() {
    this._subscriptions = new Map();
  }

  /**
   * Subscribes a callback to an event.
   */
  subscribe<T extends LektorEvent>(
    event: T,
    callback: (e: InstanceType<T>) => void
  ) {
    const eventType = event.getEventType();
    let subs = this._subscriptions.get(eventType);
    if (subs === undefined) {
      subs = new Set();
      this._subscriptions.set(eventType, subs);
    }
    subs.add(callback);
  }

  /**
   * Unsubscribes a callback from an event.
   */
  unsubscribe<T extends LektorEvent>(
    event: T,
    callback: (e: InstanceType<T>) => void
  ) {
    const eventType = event.getEventType();
    const subs = this._subscriptions.get(eventType);
    if (subs !== undefined) {
      subs.delete(callback);
    }
  }

  /**
   * Emits an event with some parameters.
   */
  emit(event: InstanceType<LektorEvent>) {
    const subs = this._subscriptions.get(event.type);
    if (subs !== undefined) {
      subs.forEach((callback) => {
        try {
          callback(event);
        } catch (e) {
          console.log(
            "Event callback failed: ",
            e,
            "callback=",
            callback,
            "event=",
            event
          );
        }
      });
    }
  }
}

const hub = new Hub();

export default hub;
