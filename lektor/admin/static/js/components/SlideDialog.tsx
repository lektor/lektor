import PropTypes from "prop-types";
import React, { MouseEvent } from "react";
import dialogSystem from "../dialogSystem";
import { trans } from "../i18n";

type Props = {
  title: string;
  hasCloseButton: boolean;
  closeOnEscape: boolean;
};

export default class SlideDialog extends React.Component<Props> {
  constructor(props: Props) {
    super(props);
    this._onKeyPress = this._onKeyPress.bind(this);
  }

  componentDidMount() {
    if (this.props.closeOnEscape) {
      window.addEventListener("keydown", this._onKeyPress);
    }
  }

  componentWillUnmount() {
    window.removeEventListener("keydown", this._onKeyPress);
  }

  _onKeyPress(event: KeyboardEvent) {
    if (event.key === "Escape" && this.props.closeOnEscape) {
      event.preventDefault();
      dialogSystem.dismissDialog();
    }
  }

  _onCloseClick(event: MouseEvent) {
    event.preventDefault();
    dialogSystem.dismissDialog();
  }

  render() {
    let { children, title, hasCloseButton } = this.props;
    return (
      <div className="sliding-panel container">
        <div className="col-md-6 col-md-offset-4">
          {hasCloseButton && (
            <a
              href="#"
              className="close-btn"
              onClick={this._onCloseClick.bind(this)}
            >
              {trans("CLOSE")}
            </a>
          )}
          <h3>{title}</h3>
          {children}
        </div>
      </div>
    );
  }
}
