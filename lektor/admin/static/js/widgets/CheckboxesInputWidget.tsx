import React from "react";
import { flipSetValue } from "../utils";
import { trans } from "../i18n";
import { WidgetProps } from "./mixins";

function checkboxIsActive(field, props: WidgetProps) {
  let value = props.value;
  if (value == null) {
    value = props.placeholder;
    if (value == null) {
      return false;
    }
  }
  for (const item of value) {
    if (item === field) {
      return true;
    }
  }
  return false;
}

export class CheckboxesInputWidget extends React.PureComponent<WidgetProps> {
  static serializeValue(value) {
    return (value || "").join(", ");
  }

  static deserializeValue(value) {
    if (value === "") {
      return null;
    }
    let rv = value.split(",").map((x) => {
      return x.match(/^\s*(.*?)\s*$/)[1];
    });
    if (rv.length === 1 && rv[0] === "") {
      rv = [];
    }
    return rv;
  }

  render() {
    let {
      className,
      value,
      placeholder,
      type,
      onChange,
      ...otherProps
    } = this.props;
    className = (className || "") + " checkbox";

    const onChangeHandler = (field, event) => {
      const newValue = flipSetValue(
        this.props.value,
        field,
        event.target.checked
      );
      onChange(newValue);
    };

    const choices = type.choices.map((item) => (
      <div className={className} key={item[0]}>
        <label>
          <input
            type="checkbox"
            {...otherProps}
            checked={checkboxIsActive(item[0], this.props)}
            onChange={(e) => onChangeHandler(item[0], e)}
          />
          {trans(item[1])}
        </label>
      </div>
    ));
    return <div className="checkboxes">{choices}</div>;
  }
}
