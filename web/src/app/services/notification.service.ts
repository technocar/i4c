import { EventEmitter, Injectable } from '@angular/core';
import { SwPush } from '@angular/service-worker';
import { Observable } from 'rxjs';

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
  private _pushWorker: SwPush;

  constructor(readonly swPush: SwPush) {
    //this.initDesktopMode();
    console.log(swPush);
    this._pushWorker = swPush;
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

  public subscribeToPushNotif(serverPublicKey: string, override: boolean): Observable<PushSubscription> {
    return new Observable<PushSubscription>(observer => {
      if (!this._pushWorker.isEnabled) {
        observer.error($localize `:@@notification_push_not_enabled:A PUSH üzenet nincs engedélyezve vagy a böngésző nem támogatja!`);
        observer.complete();
      } else {
        this._pushWorker.unsubscribe()
          .finally(() => {
            this._pushWorker.requestSubscription({
              serverPublicKey: serverPublicKey
            })
            .then(newSubscription => {
              console.log(newSubscription);
              observer.next(newSubscription);
              observer.complete();
            })
            .catch(err => {
              observer.error(err);
              observer.complete();
            });
          });
      }

      return {
        unsubscribe() {
        }
      };
    });
  }

  public unsubscribeFromPushNotif(): Observable<boolean> {
    return new Observable<boolean>(observer => {

      if (this._pushWorker.isEnabled) {
        this._pushWorker.unsubscribe().then(() => {
          observer.next(true);
          observer.complete();
        })
        .catch(err => {
          observer.error(err);
          observer.complete();
        });
      }

      return {
        unsubscribe() {
        }
      };
    });
  }
}
