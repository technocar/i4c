import { Injectable } from '@angular/core';
import {
  Router, Resolve,
  RouterStateSnapshot,
  ActivatedRouteSnapshot
} from '@angular/router';
import { Observable, of } from 'rxjs';
import { ApiService } from 'src/app/services/api.service';
import { Alarm } from 'src/app/services/models/api';

@Injectable({
  providedIn: 'root'
})
export class AlarmDetailResolver implements Resolve<Alarm> {
  constructor(private apiService: ApiService) {}

  resolve(route: ActivatedRouteSnapshot, state: RouterStateSnapshot): Observable<Alarm> {
    return this.apiService.getAlarm(route.paramMap.get("name"));
  }
}
