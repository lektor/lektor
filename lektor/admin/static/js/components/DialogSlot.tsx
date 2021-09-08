import React from "react";
import dialogSystem, { Dialog, DialogInstance } from "../dialogSystem";
import { subscribe, unsubscribe } from "../events";
import { RecordProps } from "./RecordComponent";

type State = {
  currentDialog: Dialog | null;
  currentDialogOptions: unknown;
};

class DialogSlot extends React.Component<RecordProps, State> {
  constructor(props: RecordProps) {
    super(props);
    this.state = {
      currentDialog: null,
      currentDialogOptions: null,
    };
    this.onDialogChanged = this.onDialogChanged.bind(this);
    this.initDialogInstance = this.initDialogInstance.bind(this);
  }

  componentDidMount() {
    subscribe("lektor-dialog-changed", this.onDialogChanged);
  }

  componentWillUnmount() {
    unsubscribe("lektor-dialog-changed", this.onDialogChanged);
  }

  onDialogChanged(
    event: CustomEvent<{ dialog: Dialog | null; dialogOptions?: unknown }>
  ) {
    this.setState({
      currentDialog: event.detail.dialog,
      currentDialogOptions: event.detail.dialogOptions || {},
    });
  }

  initDialogInstance(dialog: DialogInstance | null) {
    dialogSystem.notifyDialogInstance(dialog);
    window.scrollTo(0, 0);
  }

  render() {
    let dialog = null;
    if (this.state.currentDialog) {
      dialog = (
        // @ts-expect-error This is not sufficiently typed yet
        <this.state.currentDialog
          ref={this.initDialogInstance}
          dismiss={dialogSystem.dismissDialog}
          {...this.props}
          {...this.state.currentDialogOptions}
        />
      );
    } else {
      dialogSystem.notifyDialogInstance(null);
    }

    if (!dialog) {
      return null;
    }

    return (
      <div className="dialog-slot">
        {dialog}
        <div className="interface-protector" />
      </div>
    );
  }
}

export default DialogSlot;
