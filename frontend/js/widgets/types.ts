import { ComponentType, SetStateAction } from "react";
import { Translatable } from "../i18n";

export interface BaseWidgetType {
  widget: string;
  name: string;
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
  choices?: [string, Translatable][];
}

export interface Field {
  name: string;
  type: WidgetType;
  default: string | null;
  description_i18n: Translatable;
  label_i18n: Translatable;
  hide_label: boolean;
  alts_enabled: boolean | null;
}

export type WidgetProps<V = string, W = WidgetType> = {
  value: V;
  type: W;
  placeholder?: V;
  onChange: (value: SetStateAction<V>) => void;
  disabled?: boolean;
};

interface SerializableWidget {
  deserializeValue?: (value: string, type: WidgetType) => string;
  serializeValue?: (value: string, type: WidgetType) => string;
}

type FakeWidget = ComponentType<{ field: Field }> &
  SerializableWidget & {
    isFakeWidget: true;
  };
type RealWidget = ComponentType<WidgetProps> &
  SerializableWidget & {
    isFakeWidget: undefined;
  };
export type WidgetComponent = FakeWidget | RealWidget;

export function getInputClass(type: WidgetType): string {
  if (type.size === "small") {
    return "form-control input-sm";
  } else if (type.size === "large") {
    return "form-control input-lg";
  }
  return "form-control";
}
