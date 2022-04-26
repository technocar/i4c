import { Injectable } from '@angular/core';
import {
  Router, Resolve,
  RouterStateSnapshot,
  ActivatedRouteSnapshot
} from '@angular/router';
import { forkJoin, Observable, of } from 'rxjs';
import { ApiService } from 'src/app/services/api.service';
import { Alarm, AlarmGroup, Meta } from 'src/app/services/models/api';

@Injectable({
  providedIn: 'root'
})
export class AlarmDetailResolver implements Resolve<[Alarm, Meta[], AlarmGroup[]]> {
  constructor(private apiService: ApiService) {}

  resolve(route: ActivatedRouteSnapshot, state: RouterStateSnapshot): Observable<[Alarm, Meta[], AlarmGroup[]]> {
    var name = route.paramMap.get("name");
    return forkJoin([
      (name ?? "") !== "" ? this.apiService.getAlarm(name) : of(<Alarm>{
        conditions: [],
        id: -1,
        last_check: undefined,
        last_report: undefined,
        max_freq: 0,
        name: "",
        subs: [],
        subsgroup: undefined,
        window: 0
      }),
      this.apiService.getMeta(),
      this.apiService.getAlarmGroups()
    ]);
  }
}
