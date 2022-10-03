import { Injectable } from '@angular/core';
import { Observable, Observer, PartialObserver, Subscription } from 'rxjs';
import { catchError, tap } from 'rxjs/operators';
import { Download, DownloadState } from './api.service';

@Injectable({
  providedIn: 'root'
})
export class DownloadService {

  private _download$: Observable<Download>;
  private _observers: Observer<unknown>[];
  private _downloading$: Observable<Download>;
  private _downloadSubscription: Subscription;

  constructor() {
    this._observers = [];
    this._downloading$ = new Observable<Download>((observer) => {
      this._observers.push(observer);

      return {
        unsubscribe: () => {
          if (this._observers)
            this._observers.splice(this._observers.indexOf(observer), 1);
        }
      }
    });
  }

  register(download$: Observable<Download>) {
    this._download$ = download$.pipe(
      tap(d => {
        if (d.state === DownloadState.Done) {
          this._observers.forEach(v => { v.next(d); this._downloadSubscription = undefined; });
        } else {
          this._observers.forEach(v => { v.next(d); });
        }
      }),
      catchError((err, caught) => {
        this._observers.forEach(v => { v.error(err); });
        return caught;
      })
    );
    return this._download$;
  }

  download() {
    this._downloadSubscription = this._download$.subscribe();
  }

  cancelDownload() {
    if (this._downloadSubscription)
      this._downloadSubscription.unsubscribe();
  }

  subscribe(
    next?: (download: Download) => void,
    error?: (err: any) => void,
    complete?: () => void) {
    return this._downloading$.subscribe(next, error, complete);
  }

}
