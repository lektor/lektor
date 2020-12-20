import { ComponentType } from "react";
import { Translatable } from "../i18n";

export interface BaseWidgetType {
  widget: string;
  size: "normal" | "small" | "large";
  width?: string;
}

export interface WidgetType extends BaseWidgetType {
  heading_i18n?: Translatable;
  checkbox_label_i18n?: Translatable;
  addon_label_i18n?: Translatable;
}

export interface MultiWidgetType extends BaseWidgetType {
  widget: "checkboxes" | "select";
  choices: [string, Translatable][];
}

export interface Field {
  name: string;
  type: WidgetType;
  default?: string;
  description_i18n: Translatable;
  label_i18n: Translatable;
  hide_label: boolean;
  alts_enabled: boolean;
}

export type WidgetProps<V = string, W = WidgetType> = {
  value?: V;
  type: W;
  placeholder?: V;
  onChange: (value: V, uiChange?: boolean) => void;
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
