import { Event } from "./events";

class Hub {
  _subscriptions: Record<string, ((e: any) => void)[] | undefined>;
  constructor() {
    this._subscriptions = {};
  }

  /* subscribes a callback to an event */
  subscribe<T extends typeof Event>(
    event: T,
    callback: (e: InstanceType<T>) => void
  ) {
    const eventType = event.getEventType();

    let subs = this._subscriptions[eventType];
    if (subs === undefined) {
      this._subscriptions[eventType] = subs = [];
    }

    if (subs.includes(callback)) {
      return false;
    }
    subs.push(callback);
    return true;
  }

  /* unsubscribes a callback from an event */
  unsubscribe(event, callback) {
    if (typeof event !== "string") {
      event = event.getEventType();
    }

    const subs = this._subscriptions[event];
    if (subs === undefined) {
      return false;
    }

    for (let i = 0; i < subs.length; i++) {
      if (subs[i] === callback) {
        subs.splice(i, 1);
        return true;
      }
    }
    return false;
  }

  /* emits an event with some parameters */
  emit(event) {
    const subs = this._subscriptions[event.type];
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
