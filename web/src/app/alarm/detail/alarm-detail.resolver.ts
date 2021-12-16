import { Injectable } from '@angular/core';
import {
  Router, Resolve,
  RouterStateSnapshot,
  ActivatedRouteSnapshot
} from '@angular/router';
import { forkJoin, Observable, of } from 'rxjs';
import { ApiService } from 'src/app/services/api.service';
import { Alarm, Meta } from 'src/app/services/models/api';

@Injectable({
  providedIn: 'root'
})
export class AlarmDetailResolver implements Resolve<[Alarm, Meta[]]> {
  constructor(private apiService: ApiService) {}

  resolve(route: ActivatedRouteSnapshot, state: RouterStateSnapshot): Observable<[Alarm, Meta[]]> {
    return forkJoin([
      this.apiService.getAlarm(route.paramMap.get("name")),
      this.apiService.getMeta()
    ]);
  }
}
