import React, { ChangeEvent } from "react";
import { trans_obj } from "../i18n";
import { MultiWidgetType, WidgetProps } from "./types";

function checkboxIsActive(field: string, props: WidgetProps<string[]>) {
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

function flipSetValue(set: string[], value: string, isActive: boolean) {
  if (isActive) {
    return set.includes(value) ? set : [...set, value];
  } else {
    return set.filter((v) => v !== value);
  }
}

export class CheckboxesInputWidget extends React.PureComponent<
  WidgetProps<string[], MultiWidgetType>
> {
  static serializeValue(value: string[] | null) {
    return (value || []).join(", ");
  }

  static deserializeValue(value: string): string[] | null {
    if (value === "") {
      return null;
    }
    let rv = value.split(",").map((x) => x.trim());
    if (rv.length === 1 && rv[0] === "") {
      rv = [];
    }
    return rv;
  }

  render() {
    const { disabled, type, onChange } = this.props;

    const onChangeHandler = (
      field: string,
      event: ChangeEvent<HTMLInputElement>
    ) => {
      const newValue = flipSetValue(
        this.props.value || [],
        field,
        event.target.checked
      );
      onChange(newValue);
    };

    const choices = type.choices?.map((item) => (
      <div className="form-check" key={item[0]}>
        <label className="form-check-label">
          <input
            className="form-check-input"
            type="checkbox"
            disabled={disabled}
            checked={checkboxIsActive(item[0], this.props)}
            onChange={(e) => onChangeHandler(item[0], e)}
          />
          {trans_obj(item[1])}
        </label>
      </div>
    ));
    return <div className="checkboxes">{choices}</div>;
  }
}
