'use strict'

class Event {
  get type () {
    return Object.getPrototypeOf(this).constructor.getEventType()
  }

  toString () {
    return '[Event ' + this.type + ']'
  }
}

Event.getEventType = function () {
  return this.name
}

export class RecordEvent extends Event {
  constructor (options) {
    super(options = options || {})
    this.recordPath = options.recordPath
  }
}

export class AttachmentsChangedEvent extends RecordEvent {
  constructor (options) {
    super(options = options || {})
    this.attachmentsAdded = options.attachmentsAdded || []
    this.attachmentsRemoved = options.attachmentsRemoved || []
  }
}

export class DialogChangedEvent extends Event {
  constructor (options) {
    super(options = options || {})
    this.dialog = options.dialog
    this.dialogOptions = options.dialogOptions
  }
}
