import React from "react";
import dialogSystem, { Dialog, DialogInstance } from "../dialogSystem";
import { DialogChangedEvent } from "../events";
import hub from "../hub";
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
    hub.subscribe(DialogChangedEvent, this.onDialogChanged);
  }

  componentWillUnmount() {
    hub.unsubscribe(DialogChangedEvent, this.onDialogChanged);
  }

  onDialogChanged(event: DialogChangedEvent) {
    this.setState({
      currentDialog: event.dialog,
      currentDialogOptions: event.dialogOptions || {},
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
