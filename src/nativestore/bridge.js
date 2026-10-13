(() => {
  "use strict";
  const invoke = async (command, args = {}) => {
    const response = await fetch("/__nativestore/invoke", {
      method: "POST", headers: {"Content-Type": "application/json"},
      credentials: "same-origin", body: JSON.stringify({protocol: 1, command, args})
    });
    const message = await response.json();
    if (!response.ok || !message.ok) throw new Error(message.error?.message || "Request failed");
    return message.result;
  };
  const nativeCall = (module, method, ...args) => {
    const api = window.__TAURI__?.[module];
    if (!api || typeof api[method] !== "function") {
      return Promise.reject(new Error("This operation requires a NativeStore desktop window."));
    }
    return Promise.resolve(api[method](...args));
  };
  const native = Object.freeze({
    openDialog: options => nativeCall("dialog", "open", options),
    saveDialog: options => nativeCall("dialog", "save", options),
    readClipboard: () => nativeCall("clipboardManager", "readText"),
    writeClipboard: text => nativeCall("clipboardManager", "writeText", text),
    notificationPermission: () => nativeCall("notification", "isPermissionGranted"),
    requestNotificationPermission: () => nativeCall("notification", "requestPermission"),
    notify: options => nativeCall("notification", "sendNotification", options),
    window: async (operation, ...args) => {
      if (!["setTitle", "minimize", "maximize", "unmaximize", "close", "isMaximized"].includes(operation)) {
        throw new Error("Unsupported window operation");
      }
      const current = await nativeCall("window", "getCurrentWindow");
      return current[operation](...args);
    }
  });
  Object.defineProperty(window, "NativeStore", {value: Object.freeze({invoke, native}), writable: false});
})();
