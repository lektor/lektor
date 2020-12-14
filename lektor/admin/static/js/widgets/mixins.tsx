import PropTypes from "prop-types";

export const widgetPropTypes = {
  value: PropTypes.any,
  type: PropTypes.object,
  placeholder: PropTypes.any,
  onChange: PropTypes.any,
  disabled: PropTypes.bool,
};

export type WidgetProps<ValueType = string> = {
  value?: ValueType;
  type?: any;
  placeholder?: ValueType;
  onChange: (value: ValueType) => void;
  disabled?: boolean;
};

export function getInputClass(type: { size: string }) {
  let rv = "form-control";
  if (type.size === "small") {
    rv = "input-sm " + rv;
  } else if (type.size === "large") {
    rv = "input-lg " + rv;
  }
  return rv;
}
