import React, { MouseEvent } from "react";
import { trans } from "../i18n";

type Props = {
  title: string;
  hasCloseButton: boolean;
  dismiss: () => void;
};

export default class SlideDialog extends React.Component<Props> {
  constructor(props: Props) {
    super(props);
    this.onKeyPress = this.onKeyPress.bind(this);
    this.onCloseClick = this.onCloseClick.bind(this);
  }

  componentDidMount() {
    window.addEventListener("keydown", this.onKeyPress);
  }

  componentWillUnmount() {
    window.removeEventListener("keydown", this.onKeyPress);
  }

  onKeyPress(event: KeyboardEvent) {
    if (event.key === "Escape") {
      event.preventDefault();
      this.props.dismiss();
    }
  }

  onCloseClick(event: MouseEvent) {
    event.preventDefault();
    this.props.dismiss();
  }

  render() {
    const { children, title, hasCloseButton } = this.props;
    return (
      <div className="sliding-panel container">
        <div className="col-md-6 offset-md-3">
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
