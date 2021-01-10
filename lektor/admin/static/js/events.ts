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
  recordPath: string | null;

  constructor(options: { recordPath: string | null }) {
    super();
    this.recordPath = options.recordPath;
  }
}

export class DialogChangedEvent extends BaseEvent {
  dialog: Dialog | null;
  dialogOptions?: unknown;
  constructor(options: { dialog: Dialog | null; dialogOptions?: unknown }) {
    super();
    this.dialog = options.dialog;
    this.dialogOptions = options.dialogOptions;
  }
}

export type LektorEvent =
  | typeof AttachmentsChangedEvent
  | typeof DialogChangedEvent;
