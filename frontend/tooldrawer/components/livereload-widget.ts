import { css, html, LitElement, ReactiveController } from "lit";
import { customElement, property, query } from "lit/decorators.js";
import { WidgetMixin } from "./widget";

import "./checkbox-button";
import "./icon";

declare global {
  interface HTMLElementTagNameMap {
    "lektor-livereload-widget": LivereloadWidget;
  }
}

interface LivereloaderInterface {
  disabled: boolean;
}

type CheckboxButtonElement = HTMLElementTagNameMap["lektor-checkbox-button"];

/**
 * A button that can be used to enable/disable live-reloading.
 *
 * This widget initializes and saves its disabled state in the
 * query string of document.location.
 */
@customElement("lektor-livereload-widget")
export class LivereloadWidget extends WidgetMixin(LitElement) {
  /**
   * True if livereload should currently be disabled.
   *
   * A "change" event is emitted whenever this changes state.
   */
  @property({ attribute: false })
  livereloadDisabled = true;

  @property({ attribute: false })
  livereloader?: LivereloaderInterface;

  @property({ attribute: false })
  override widgetRole: CheckboxButtonElement["widgetRole"] = "switch";

  @query("lektor-checkbox-button", true)
  private _checkbox!: CheckboxButtonElement;

  private _queryParam = new QueryParamController(this, {
    paramName: "livereload",
  });

  static override shadowRootOptions = {
    ...LitElement.shadowRootOptions,
    delegatesFocus: true,
  };

  override willUpdate() {
    if (this.livereloader) {
      this.livereloader.disabled = this.livereloadDisabled;
    }
  }

  override render() {
    /* eslint-disable @typescript-eslint/unbound-method */
    return html`
      <lektor-checkbox-button
        .checked=${!this.livereloadDisabled}
        @change=${this._onchange}
        .widgetRole=${this.widgetRole}
        .label=${this.label}
        .tooltip=${this.tooltip}
      >
        <lektor-icon icon="faRetweet"></lektor-icon>
      </lektor-checkbox-button>
    `;
    /* eslint-enable */
  }

  private _onchange() {
    this.livereloadDisabled = this._queryParam.disabled =
      !this._checkbox.checked;
    this.dispatchEvent(new Event("change", { bubbles: true }));
  }

  static override styles = css`
    lektor-icon {
      position: relative;
    }
    lektor-checkbox-button:not([checked]) lektor-icon::before {
      /* red slash over icon when unchecked */
      --slash-color: var(--lektor-button-slash-color, hsl(349, 80%, 45%));
      content: "";
      position: absolute;
      left: 0;
      top: 0;
      width: 100%;
      height: 100%;
      background: linear-gradient(
        to left top,
        transparent 45%,
        var(--slash-color) 46%,
        var(--slash-color) 54%,
        transparent 55%
      );
      opacity: 0.9;
    }
  `;
}

/*
 * Controller to manage the ?livereload query param in the window location
 */
class QueryParamController implements ReactiveController {
  private host: LivereloadWidget;
  private paramName: string;

  constructor(host: LivereloadWidget, { paramName }: { paramName: string }) {
    this.host = host;
    this.paramName = paramName;
    host.addController(this);
  }

  hostConnected() {
    window.addEventListener("popstate", this._update);
    window.addEventListener("load", this._update);
    this._update();
  }

  hostDisconnected() {
    window.removeEventListener("popstate", this._update);
    window.removeEventListener("load", this._update);
    this.host.livereloadDisabled = true;
  }

  private _update = () => {
    const disabled = this.disabled;
    if (Boolean(this.host.livereloadDisabled) !== disabled) {
      this.host.livereloadDisabled = disabled;
      this.host.dispatchEvent(new Event("change", { bubbles: true }));
    }
  };

  get disabled() {
    const searchParams = new URLSearchParams(location.search);
    const value = searchParams.get(this.paramName);
    return /^(false|no|0)$/i.test(value || "");
  }

  set disabled(value: boolean) {
    if (Boolean(value) !== this.disabled) {
      const url = new URL(window.location.href);
      if (value) {
        url.searchParams.set(this.paramName, "false");
      } else {
        url.searchParams.delete(this.paramName);
      }
      window.history.pushState(null, "", url.href);
    }
  }
}
