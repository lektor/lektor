import hub from "./hub";
import { DialogChangedEvent } from "./events";
import FindFiles from "./dialogs/findFiles";
import ErrorDialog from "./dialogs/errorDialog";
import Publish from "./dialogs/publish";
import Refresh from "./dialogs/Refresh";

export type Dialog =
  | typeof FindFiles
  | typeof ErrorDialog
  | typeof Publish
  | typeof Refresh;

export type DialogInstance = InstanceType<Dialog> & {
  preventNavigation?: () => boolean;
};

class DialogSystem {
  private instance: DialogInstance | null;

  constructor() {
    this.instance = null;
  }

  // invoked by the application once the dialog has been created.
  notifyDialogInstance(dialog: DialogInstance | null) {
    this.instance = dialog;
  }

  // given a dialog class this will instruct the application to bring up
  // the dialog and display it.
  showDialog(dialog: Dialog, options?: unknown) {
    // if the current dialog prevents navigation, then we just silently
    // will not show the dialog.
    if (!this.preventNavigation()) {
      hub.emit(
        new DialogChangedEvent({
          dialog: dialog,
          dialogOptions: options || {},
        })
      );
    }
  }

  // tells the application to dismiss the current dialog.
  dismissDialog() {
    if (!this.preventNavigation()) {
      hub.emit(
        new DialogChangedEvent({
          dialog: null,
        })
      );
    }
  }

  // indicates if a dialog is shown
  dialogIsOpen() {
    return !!this.instance;
  }

  // returns true if the current dialog prevents navigation.
  preventNavigation() {
    return (
      this.instance &&
      this.instance.preventNavigation !== undefined &&
      this.instance.preventNavigation()
    );
  }
}

const dialogSystem = new DialogSystem();

export default dialogSystem;
