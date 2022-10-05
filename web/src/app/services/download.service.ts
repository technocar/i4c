import { Injectable } from '@angular/core';
import { Observable, Observer, PartialObserver, Subscription, throwError } from 'rxjs';
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
        if (d.state === DownloadState.Done && d.statusCode === 200) {
          this._observers.forEach(v => { v.next(d); });
          this._downloadSubscription.unsubscribe();
        } else if (d.statusCode >= 400) {
          this._downloadSubscription.unsubscribe();
          throwError(d.statusCode);
        } else {
          this._observers.forEach(v => { v.next(d); });
        }
      }),
      catchError((err, caught) => {
        var d: Download = {
          content: null,
          state: DownloadState.Done,
          progress: 0,
          statusCode: err.statusCode,
          error: err
        }
        this._observers.forEach(v => { v.next(d) });
        this._downloadSubscription.unsubscribe();
        throw err;
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
