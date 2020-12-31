import ErrorDialog from "./dialogs/errorDialog";
import dialogSystem from "./dialogSystem";

export function bringUpDialog(error: unknown) {
  dialogSystem.showDialog(ErrorDialog, { error }, false);
}
