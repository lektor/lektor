import { Dialog } from "./dialogSystem";

export class Event {
  get type() {
    return Object.getPrototypeOf(this).constructor.getEventType();
  }

  toString() {
    return "[Event " + this.type + "]";
  }
}

Event.getEventType = function () {
  return this.name;
};

export class AttachmentsChangedEvent extends Event {
  attachmentsAdded: unknown[];
  attachmentsRemoved: unknown[];
  recordPath: string | null;
  constructor(options: {
    recordPath: string | null;
    attachmentsAdded?: unknown[];
    attachmentsRemoved?: unknown[];
  }) {
    super();
    this.recordPath = options.recordPath;
    this.attachmentsAdded = options.attachmentsAdded || [];
    this.attachmentsRemoved = options.attachmentsRemoved || [];
  }
}

export class DialogChangedEvent extends Event {
  dialog: Dialog | null;
  dialogOptions?: unknown;
  constructor(options: { dialog: Dialog | null; dialogOptions?: unknown }) {
    super();
    this.dialog = options.dialog;
    this.dialogOptions = options.dialogOptions;
  }
}
