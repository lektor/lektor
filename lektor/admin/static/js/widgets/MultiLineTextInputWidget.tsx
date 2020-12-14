import React, {
  ChangeEvent,
  Component,
  createRef,
  CSSProperties,
  RefObject,
} from "react";
import { getInputClass, WidgetProps } from "./mixins";

export class MultiLineTextInputWidget extends Component<WidgetProps> {
  textarea: RefObject<HTMLTextAreaElement>;

  constructor(props: WidgetProps) {
    super(props);
    this.recalculateSize = this.recalculateSize.bind(this);
    this.textarea = createRef();
  }

  onChange(event: ChangeEvent<HTMLTextAreaElement>) {
    this.recalculateSize();
    this.props.onChange(event.target.value);
  }

  componentDidMount() {
    this.recalculateSize();
    window.addEventListener("resize", this.recalculateSize);
  }

  componentWillUnmount() {
    window.removeEventListener("resize", this.recalculateSize);
  }

  componentDidUpdate() {
    this.recalculateSize();
  }

  isInAutoResizeMode() {
    return this.props.rows === undefined;
  }

  recalculateSize() {
    if (!this.isInAutoResizeMode()) {
      return;
    }
    let diff;
    const node = this.textarea.current;

    if (window.getComputedStyle) {
      const s = window.getComputedStyle(node);
      if (
        s.getPropertyValue("box-sizing") === "border-box" ||
        s.getPropertyValue("-moz-box-sizing") === "border-box" ||
        s.getPropertyValue("-webkit-box-sizing") === "border-box"
      ) {
        diff = 0;
      } else {
        diff =
          parseInt(s.getPropertyValue("padding-bottom") || 0, 10) +
          parseInt(s.getPropertyValue("padding-top") || 0, 10);
      }
    } else {
      diff = 0;
    }

    const updateScrollPosition = node === document.activeElement;
    // Cross-browser compatibility for scroll position
    const oldScrollTop =
      document.documentElement.scrollTop || document.body.scrollTop;
    const oldHeight = node.offsetHeight;

    node.style.height = "auto";
    const newHeight = node.scrollHeight - diff;
    node.style.height = newHeight + "px";

    if (updateScrollPosition) {
      window.scrollTo(
        document.body.scrollLeft,
        oldScrollTop + (newHeight - oldHeight)
      );
    }
  }

  render() {
    const { type, value, placeholder, disabled } = this.props;

    const style: CSSProperties = this.isInAutoResizeMode()
      ? {
          display: "block",
          overflow: "hidden",
          resize: "none",
        }
      : {};

    return (
      <div>
        <textarea
          ref={this.textarea}
          className={getInputClass(type)}
          onChange={this.onChange.bind(this)}
          style={style}
          value={value}
          disabled={disabled}
          placeholder={placeholder}
        />
      </div>
    );
  }
}
