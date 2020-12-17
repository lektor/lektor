import { ComponentType } from "react";

type Translations = Partial<Record<string, string>>;

interface BaseWidgetType {
  widget: string;
  size: "normal" | "small" | "large";
}

export interface WidgetType extends BaseWidgetType {
  heading_i18n?: Translations;
  checkbox_label_i18n?: Translations;
  addon_label_i18n?: Translations;
}

export interface MultiWidgetType extends BaseWidgetType {
  widget: "checkboxes" | "select";
  choices: [string, Translations][];
}

export interface Field {
  name: string;
  type: WidgetType;
  description_i18n: Translations;
  label_i18n: Translations;
}

export type WidgetProps<V = string, W = WidgetType> = {
  value?: V;
  type: W;
  placeholder?: V;
  onChange: (value: V) => void;
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
