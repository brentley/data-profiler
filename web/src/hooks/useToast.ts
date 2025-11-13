// Toast management hook
import { useState, useCallback } from 'react';
import type { ToastProps, ToastType } from '../components/Toast';

export function useToast() {
  const [toasts, setToasts] = useState<ToastProps[]>([]);

  const addToast = useCallback(
    (type: ToastType, title: string, message: string, duration?: number) => {
      const id = `toast-${Date.now()}-${Math.random()}`;
      const toast: ToastProps = {
        id,
        type,
        title,
        message,
        duration,
        onClose: (toastId: string) => {
          setToasts((prev) => prev.filter((t) => t.id !== toastId));
        },
      };
      setToasts((prev) => [...prev, toast]);
      return id;
    },
    []
  );

  const success = useCallback(
    (title: string, message: string, duration?: number) =>
      addToast('success', title, message, duration),
    [addToast]
  );

  const error = useCallback(
    (title: string, message: string, duration?: number) =>
      addToast('error', title, message, duration),
    [addToast]
  );

  const warning = useCallback(
    (title: string, message: string, duration?: number) =>
      addToast('warning', title, message, duration),
    [addToast]
  );

  const info = useCallback(
    (title: string, message: string, duration?: number) =>
      addToast('info', title, message, duration),
    [addToast]
  );

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const clearAll = useCallback(() => {
    setToasts([]);
  }, []);

  return {
    toasts,
    success,
    error,
    warning,
    info,
    removeToast,
    clearAll,
  };
}
