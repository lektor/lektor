import PropTypes from "prop-types";
import { ComponentType } from "react";

export const widgetPropTypes = {
  value: PropTypes.any,
  type: PropTypes.object,
  placeholder: PropTypes.any,
  onChange: PropTypes.any,
  disabled: PropTypes.bool,
};

type Translations = Partial<Record<string, string>>;

export interface WidgetType {
  widget: string;
  heading_i18n?: Translations;
  checkbox_label_i18n?: Translations;
  addon_label_i18n?: Translations;
  size?: string;
}

export interface Field {
  name: string;
  type: WidgetType;
  description_i18n: Translations;
  label_i18n: Translations;
}

export type WidgetProps<ValueType = string> = {
  value?: ValueType;
  type: WidgetType;
  placeholder?: ValueType;
  onChange: (value: ValueType) => void;
  disabled?: boolean;
};

type FakeWidget = ComponentType<{ field: Field }> & { isFakeWidget: true };
type RealWidget = ComponentType<WidgetProps> & { isFakeWidget: undefined };
export type WidgetComponent = FakeWidget | RealWidget;

export function getInputClass(type: WidgetType) {
  let rv = "form-control";
  if (type.size === "small") {
    rv = "input-sm " + rv;
  } else if (type.size === "large") {
    rv = "input-lg " + rv;
  }
  return rv;
}
