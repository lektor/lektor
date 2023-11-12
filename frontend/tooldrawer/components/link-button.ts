import { html, LitElement, nothing } from "lit";
import { customElement, property } from "lit/decorators.js";
import { WidgetMixin } from "./widget";
import buttonStyles from "./css/button";

declare global {
  interface HTMLElementTagNameMap {
    "lektor-link-button": LinkButton;
  }
}

/**
 * A link styled as a button.
 */
@customElement("lektor-link-button")
export class LinkButton extends WidgetMixin(LitElement) {
  @property()
  href: string = "";

  @property({ attribute: false })
  override widgetRole: "link" | "button" | "menuitem" = "link";

  override render() {
    return html`
      <a
        href=${this.href}
        class="button"
        role=${this.widgetRole !== "link" ? this.widgetRole : nothing}
        title=${(this.tooltip ?? this.label) || nothing}
        aria-label=${this.label}
      >
        <slot></slot>
      </a>
    `;
  }

  static override shadowRootOptions = {
    ...LitElement.shadowRootOptions,
    delegatesFocus: true,
  };

  static override styles = buttonStyles;
}
