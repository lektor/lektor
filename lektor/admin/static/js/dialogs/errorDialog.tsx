import React, { Component } from "react";
import SlideDialog from "../components/SlideDialog";
import { trans } from "../i18n";

export default class ErrorDialog extends Component<
  { dismiss: () => void; error: any },
  unknown
> {
  render() {
    return (
      <SlideDialog
        dismiss={this.props.dismiss}
        hasCloseButton
        title={trans("ERROR")}
      >
        <p>
          {trans("ERROR_OCURRED")}
          {": "}
          {trans("ERROR_" + this.props.error.code)}
        </p>
        <p>
          <button
            type="submit"
            className="btn btn-primary"
            onClick={this.props.dismiss}
          >
            {trans("CLOSE")}
          </button>
        </p>
      </SlideDialog>
    );
  }
}
