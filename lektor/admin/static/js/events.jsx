'use strict'

import React from 'react'


class Event {

  constructor(options) {
  }

  get type() {
    return Object.getPrototypeOf(this).constructor.getEventType();
  }

  toString() {
    return '[Event ' + this.type + ']';
  }
}

Event.getEventType = function() {
  return this.name;
}


class RecordEvent extends Event {

  constructor(options) {
    super(options = options || {});
    this.recordPath = options.recordPath;
  }
}


class AttachmentsChangedEvent extends RecordEvent {

  constructor(options) {
    super(options = options || {});
    this.attachmentsAdded = options.attachmentsAdded || [];
    this.attachmentsRemoved = options.attachmentsRemoved || [];
  }
}


class DialogChangedEvent extends Event {

  constructor(options) {
    super(options = options || {});
    this.dialog = options.dialog;
    this.dialogOptions = options.dialogOptions;
  }
}


export default {
  Event: Event,
  RecordEvent: RecordEvent,
  AttachmentsChangedEvent: AttachmentsChangedEvent,
  DialogChangedEvent: DialogChangedEvent,
}
