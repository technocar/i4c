import { Injectable } from '@angular/core';
import {
  Router, Resolve,
  RouterStateSnapshot,
  ActivatedRouteSnapshot
} from '@angular/router';
import { forkJoin, Observable, of } from 'rxjs';
import { ApiService } from 'src/app/services/api.service';
import { AuthenticationService } from 'src/app/services/auth.service';
import { AlarmNotificationType, AlarmSubscription, AlarmSubscriptionGroupGrant, StatusType } from 'src/app/services/models/api';

@Injectable({
  providedIn: 'root'
})
export class AlarmSubscriptionDetailResolver implements Resolve<Observable<[AlarmSubscription, AlarmSubscriptionGroupGrant[]]>> {

  constructor(
    private apiService: ApiService)
  {}

  resolve(route: ActivatedRouteSnapshot, state: RouterStateSnapshot): Observable<[AlarmSubscription, AlarmSubscriptionGroupGrant[]]> {
    var id = parseInt(route.paramMap.get("id"));
    var user = route.paramMap.get("user");
    var detail: Observable<AlarmSubscription>;
    if (id === -1) {
      detail = of({
        id: undefined,
        address: undefined,
        address_name: "új feliratkozás...",
        groups: [],
        method: AlarmNotificationType.None,
        user: user,
        status: StatusType.Active,
        user_name: user
      });
    } else {
      detail = this.apiService.getAlarmSubscription(id);
    }
    return forkJoin([detail, this.apiService.getAlarmGroups(user)]);
  }
}
