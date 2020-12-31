import { Dialog } from "./dialogSystem";

export class BaseEvent {
  get type() {
    return Object.getPrototypeOf(this).constructor.getEventType();
  }

  toString() {
    return "[Event " + this.type + "]";
  }

  static getEventType() {
    return this.name;
  }
}

export class AttachmentsChangedEvent extends BaseEvent {
  constructor(readonly recordPath: string | null) {
    super();
  }
}

export class DialogChangedEvent extends BaseEvent {
  constructor(
    readonly dialog: Dialog | null,
    readonly dialogOptions?: unknown
  ) {
    super();
  }
}

export type LektorEvent =
  | typeof AttachmentsChangedEvent
  | typeof DialogChangedEvent;
