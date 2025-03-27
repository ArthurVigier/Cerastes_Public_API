import React, { useEffect } from 'react';
import { useUIStore } from '../../store/ui';

interface NotificationProps {
  id: string;
  message: string;
  type: 'success' | 'error' | 'info' | 'warning';
}

export default function Notification({ id, message, type }: NotificationProps) {
  const removeNotification = useUIStore((state) => state.removeNotification);

  useEffect(() => {
    const timer = setTimeout(() => {
      removeNotification(id);
    }, 5000);

    return () => clearTimeout(timer);
  }, [id, removeNotification]);

  const bgColor = {
    success: 'bg-green-500',
    error: 'bg-red-500',
    info: 'bg-blue-500',
    warning: 'bg-yellow-500',
  };

  return (
    <div className={`${bgColor[type]} text-white p-4 rounded-md shadow-lg max-w-md`}>
      <div className="flex justify-between">
        <p>{message}</p>
        <button onClick={() => removeNotification(id)} className="ml-4">
          ✕
        </button>
      </div>
    </div>
  );
}

export function NotificationContainer() {
  const notifications = useUIStore((state) => state.notifications);

  return (
    <div className="fixed top-4 right-4 z-50 space-y-4">
      {notifications.map((notification) => (
        <Notification key={notification.id} {...notification} />
      ))}
    </div>
  );
}