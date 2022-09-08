import { css, html, nothing, LitElement } from "lit";
import { customElement, property, query } from "lit/decorators.js";
import { classMap } from "lit/directives/class-map.js";
import { WidgetMixin } from "./widget";
import buttonStyle from "./css/button";
import visuallyHiddenStyle from "./css/visually-hidden";

declare global {
  interface HTMLElementTagNameMap {
    "lektor-checkbox-button": CheckboxButton;
  }
}

/**
 * A toggle button implemented with a checkbox input.
 *
 * The checkbox is visually hidden. Its label is styled as a button.
 *
 * Doing things this way aids accessibility if the semantics of a checkbox
 * are what's needed.
 *
 * Idea from:
 * https://getbootstrap.com/docs/5.3/forms/checks-radios/#checkbox-toggle-buttons
 */
@customElement("lektor-checkbox-button")
export class CheckboxButton extends WidgetMixin(LitElement) {
  /**
   * True iff the underlying checkbox is checked.
   *
   * A "change" event is generated whenever this property changes state.
   */
  @property({ type: Boolean, reflect: true })
  checked: boolean = false;

  @property({ attribute: false })
  override widgetRole: "checkbox" | "menuitemcheckbox" | "switch" = "checkbox";

  override render() {
    /* eslint-disable @typescript-eslint/unbound-method */
    return html`
      <input
        id="cb"
        type="checkbox"
        class="visually-hidden"
        .checked=${this.checked}
        @change=${this._onchange}
        @keyup=${this._onkeyup}
        role=${this.widgetRole !== "checkbox" ? this.widgetRole : nothing}
        aria-checked=${this.widgetRole === "switch" ? this.checked : nothing}
      />
      <label
        for="cb"
        class=${classMap({ button: true, active: this.checked })}
        title=${(this.tooltip ?? this.label) || nothing}
      >
        <span class="visually-hidden">${this.label}</span>
        <slot></slot>
      </label>
    `;
    /* eslint-enable */
  }

  @query("input", true)
  private _checkbox!: HTMLInputElement;

  private _onchange() {
    this.checked = this._checkbox.checked;
    // NB: Native change events are not composed (they don't propagate out of
    // the shadow DOM). So send a synthetic change event.
    this.dispatchEvent(new Event("change", { bubbles: true }));
  }

  private _onkeyup(event: KeyboardEvent) {
    // Native checkboxes activate on <Space>. We augment that to
    // activate on <Return>, too, as is normal for buttons.
    if (event.code === "Enter") {
      event.preventDefault();
      this.checked = !this.checked;
    }
  }

  static override shadowRootOptions = {
    ...LitElement.shadowRootOptions,
    delegatesFocus: true,
  };

  static override styles = [
    buttonStyle,
    visuallyHiddenStyle,
    css`
      /*
       * Attempt to replicate browser's native focus style for the label
       *
       * https://css-tricks.com/copy-the-browsers-native-focus-styles/
       */
      input:focus-visible + label {
        outline: 5px auto black;
        outline-offset: 1px;
        outline-color: Highlight;
        outline-color: -webkit-focus-ring-color;
      }
    `,
  ];
}
