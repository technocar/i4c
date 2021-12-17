import { EventEmitter, Injectable } from '@angular/core';

export enum AppNotifType { Info = "info", Success = "success", Warning = "warning", Error = "danger"  }
export interface AppNotif {
  type: AppNotifType,
  message: string,
  autoClose: boolean,
  id: number
}

@Injectable({
  providedIn: 'root'
})
export class NotificationService {

  receiveAppNotif: EventEmitter<AppNotif> = new EventEmitter();

  private _desktopModeEnabled: boolean = false;

  constructor() {
    //this.initDesktopMode();
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

  public sendAppNotif(type: AppNotifType, message: string) {
    this.receiveAppNotif.emit({
      type: type,
      message: message,
      autoClose: type === AppNotifType.Success,
      id: -1
    });
  }
}
