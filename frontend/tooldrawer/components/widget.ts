import { LitElement } from "lit";
import { property } from "lit/decorators.js";

export declare class WidgetInterface extends LitElement {
  /**
   * The ARIA role to assign to the control element within the widget.
   */
  widgetRole: string;

  /**
   * The a11y label to apply to the control element within the widget.
   */
  label: string;

  /**
   * Tooltip to display when the control is hovered.
   *
   * If unset, defaults to the value of the label property.
   * Set to empty string to disable tooltip.
   */
  tooltip: string | undefined;
}

export type WidgetRole =
  | "widget"
  | "scrollbar"
  | "searchbox"
  | "separator" // ?
  | "slider"
  | "spinbutton"
  | "switch"
  | "tab"
  | "tabpanel"
  | "treeitem"
  | "button"
  | "checkbox"
  | "gridcell"
  | "link"
  | "menuitem"
  | "menuitemcheckbox"
  | "menuitemradio"
  | "option"
  | "progressbar"
  | "radio"
  | "textbox";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type Constructor<T = object> = new (...args: any[]) => T;

export function WidgetMixin<T extends Constructor<LitElement>>(Base: T) {
  class WidgetClass extends Base implements WidgetInterface {
    @property({ attribute: false })
    widgetRole: WidgetRole = "widget";

    @property()
    label: string = "";

    @property()
    tooltip: string | undefined;
  }
  return WidgetClass as Constructor<WidgetInterface> & T;
}
