import { css } from "lit";

export default css`
  .visually-hidden {
    position: absolute;
    height: 1px;
    width: 1px;
    clip: rect(0 0 0 0);
    clip-path: inset(50%);
    overflow: hidden;
    white-space: nowrap;
  }
`;
