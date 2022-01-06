import React, { useCallback, useState } from "react";
import { useLektorEvent } from "../events";

import "./Notifications.css";

export default function Notifications(): JSX.Element {
  const [notifications, setNotifications] = useState<{ message: string }[]>([]);

  const addNotification = useCallback((s: string) => {
    const notification = { message: s };
    setNotifications((ns) => [...ns, notification]);
    setTimeout(() => {
      setNotifications((ns) => ns.filter((n) => n !== notification));
    }, 3000);
  }, []);

  useLektorEvent(
    "lektor-notification",
    useCallback(
      (ev) => {
        addNotification(ev.detail.message);
      },
      [addNotification]
    )
  );

  return (
    <div className="notifications">
      {notifications.map(({ message }, i) => (
        <div
          key={`${message};${i}`}
          className="alert alert-success"
          role="alert"
        >
          {message}
        </div>
      ))}
    </div>
  );
}
