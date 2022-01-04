import React, { MouseEvent, useCallback, useState } from "react";

export default function ToggleGroup({
  className = "",
  groupTitle,
  children,
}: {
  className?: string;
  groupTitle: string;
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(false);

  const toggle = useCallback((event: MouseEvent) => {
    event.preventDefault();
    setOpen((v) => !v);
  }, []);

  return (
    <div
      className={`${className} toggle-group ${
        open ? "toggle-group-open" : "toggle-group-closed"
      }`}
    >
      <div className="header">
        <h4 className="toggle" onClick={toggle}>
          {groupTitle}
        </h4>
      </div>
      <div className="children">{children}</div>
    </div>
  );
}
