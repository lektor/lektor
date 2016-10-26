"use strict"

import React from 'react'
import hub from './hub'
import {DialogChangedEvent} from './events'


class DialogSystem {

  constructor() {
    this._dialogInstance = null;
  }

  // invoked by the application once the dialog has been created.
  notifyDialogInstance(dialog) {
    this._dialogInstance = dialog;
  }

  // given a dialog class this will instruct the application to bring up
  // the dialog and display it.
  showDialog(dialog, options) {
    // if the current dialog prevents navigation, then we just silently
    // will not show the dialog.
    if (!this.preventNavigation()) {
      hub.emit(new DialogChangedEvent({
        dialog: dialog,
        dialogOptions: options || {}
      }));
    }
  }

  // tells the application to dismiss the current dialog.
  dismissDialog() {
    if (!this.preventNavigation()) {
      hub.emit(new DialogChangedEvent({
        currentDialog: null
      }));
    }
  }

  // indicates if a dialog is shown
  dialogIsOpen() {
    return !!this._dialogInstance;
  }

  // returns true if the current dialog prevents navigation.
  preventNavigation() {
    return (
      this._dialogInstance &&
      this._dialogInstance.preventNavigation !== undefined &&
      this._dialogInstance.preventNavigation()
    );
  }
}

const dialogSystem = new DialogSystem()


export default dialogSystem
