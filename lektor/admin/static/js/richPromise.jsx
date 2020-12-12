import ErrorDialog from "./dialogs/errorDialog";
import dialogSystem from "./dialogSystem";

export function bringUpDialog(error) {
  if (!dialogSystem.dialogIsOpen()) {
    dialogSystem.showDialog(ErrorDialog, {
      error: error,
    });
  }
}
