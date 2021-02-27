import React, { ChangeEvent, createRef, RefObject } from "react";
import { WidgetProps } from "./types";
import { trans_obj } from "../i18n";

function isTrue(value?: string) {
  return value === "true" || value === "yes" || value === "1";
}

export class BooleanInputWidget extends React.Component<WidgetProps, unknown> {
  checkbox: RefObject<HTMLInputElement>;

  constructor(props: WidgetProps) {
    super(props);
    this.checkbox = createRef();
    this.onChange = this.onChange.bind(this);
  }

  onChange(event: ChangeEvent<HTMLInputElement>) {
    this.props.onChange(event.target.checked ? "yes" : "no");
  }

  componentDidMount() {
    const checkbox = this.checkbox.current;
    if (checkbox) {
      if (!this.props.value && this.props.placeholder) {
        checkbox.indeterminate = true;
        checkbox.checked = isTrue(this.props.placeholder);
      } else {
        checkbox.indeterminate = false;
      }
    }
  }

  render() {
    const { type, value, disabled } = this.props;

    return (
      <div className="form-check">
        <label className="form-check-label">
          <input
            type="checkbox"
            className="form-check-input"
            disabled={disabled}
            ref={this.checkbox}
            checked={isTrue(value)}
            onChange={this.onChange}
          />
          {type.checkbox_label_i18n
            ? trans_obj(type.checkbox_label_i18n)
            : null}
        </label>
      </div>
    );
  }
}
