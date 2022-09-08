import { css } from "lit";

export default css`
  .button {
    --default-color: hsl(336, 33%, 43%);
    --default-border-color: hsl(24, 2%, 80%);

    padding: 2px 3px;
    border: 1px outset
      var(--lektor-button-border-color, var(--default-border-color));
    border-radius: 3px;

    color: var(--lektor-button-color, var(--default-color));
    background-color: var(--lektor-button-bg, hsl(24, 5%, 93%));

    aspect-ratio: 1/1;
    cursor: pointer;
  }
  .button:hover {
    color: var(--lektor-button-hover-color, var(--default-color));
    background-color: var(--lektor-button-hover-bg, hsl(24, 7%, 98%));
    border-color: var(--lektor-button-border-hover-color, hsl(24, 2%, 67%));
  }
  .button:active,
  .button.active:not(:hover) {
    color: var(--lektor-button-active-color, var(--default-color));
    background-color: var(--lektor-button-active-bg, hsl(24, 5%, 87%));
    border-color: var(
      --lektor-button-border-active-color,
      var(--default-border-color)
    );
  }
  .button:active,
  .button.active {
    border-style: inset;
  }

  .button {
    display: flex;
    justify-content: center;
    align-items: center;
  }
`;
