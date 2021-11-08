import { Injectable } from '@angular/core';

@Injectable({
  providedIn: 'root'
})
export class NotificationService {

  private _desktopModeEnabled: boolean = false;

  constructor() {
    this.initDesktopMode();
  }

  private initDesktopMode() {

    function checkNotificationPromise() {
      try {
        Notification.requestPermission().then();
      } catch(e) {
        return false;
      }
      return true;
    }

    if ("Notification" in window) {
      if (Notification.permission === "granted")
        this._desktopModeEnabled = true;
      else if (Notification.permission !== "denied") {
        if (checkNotificationPromise()) {
          Notification.requestPermission().then((permission) => {
            if (permission === "granted")
              this._desktopModeEnabled = true;
          });
        } else {
          Notification.requestPermission((permission) => {
            if (permission === "granted")
              this._desktopModeEnabled = true;
          });
        }
      }
    }
  }

  public sendDesktopNotif(title: string, message: string) {
    if (!this._desktopModeEnabled)
      return;

    new Notification(title, { body: message, timestamp: Date.now() });
  }
}
