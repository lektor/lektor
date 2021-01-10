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
    this.onKeyPress = this.onKeyPress.bind(this);
    this.onCloseClick = this.onCloseClick.bind(this);
  }

  componentDidMount() {
    if (this.props.closeOnEscape) {
      window.addEventListener("keydown", this.onKeyPress);
    }
  }

  componentWillUnmount() {
    window.removeEventListener("keydown", this.onKeyPress);
  }

  onKeyPress(event: KeyboardEvent) {
    if (event.key === "Escape" && this.props.closeOnEscape) {
      event.preventDefault();
      dialogSystem.dismissDialog();
    }
  }

  onCloseClick(event: MouseEvent) {
    event.preventDefault();
    dialogSystem.dismissDialog();
  }

  render() {
    const { children, title, hasCloseButton } = this.props;
    return (
      <div className="sliding-panel container">
        <div className="col-md-6 col-md-offset-4">
          {hasCloseButton && (
            <a href="#" className="close-btn" onClick={this.onCloseClick}>
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
