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
      className={
        open ? `${className} toggle-group` : `${className} toggle-group closed`
      }
    >
      <h4 className="toggle-group-header" onClick={toggle}>
        {groupTitle}
      </h4>
      <div className="toggle-group-content">{children}</div>
    </div>
  );
}
