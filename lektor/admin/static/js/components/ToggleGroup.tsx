import React, { MouseEvent } from "react";

type Props = {
  className?: string;
  groupTitle: string;
  defaultVisibility: boolean;
};
type State = {
  isVisible: boolean;
};

export default class ToggleGroup extends React.Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = {
      isVisible: props.defaultVisibility,
    };
    this.toggle = this.toggle.bind(this);
  }

  toggle(event: MouseEvent) {
    event.preventDefault();
    this.setState((state) => ({ isVisible: !state.isVisible }));
  }

  render() {
    const { groupTitle, children } = this.props;
    let className = (this.props.className || "") + " toggle-group";
    if (this.state.isVisible) {
      className += " toggle-group-open";
    } else {
      className += " toggle-group-closed";
    }

    return (
      <div className={className}>
        <div className="header">
          <h4 className="toggle" onClick={this.toggle}>
            {groupTitle}
          </h4>
        </div>
        <div className="children">{children}</div>
      </div>
    );
  }
}
