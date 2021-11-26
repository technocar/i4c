import { Injectable } from '@angular/core';
import {
  Router, Resolve,
  RouterStateSnapshot,
  ActivatedRouteSnapshot
} from '@angular/router';
import { forkJoin, Observable, of } from 'rxjs';
import { ApiService } from 'src/app/services/api.service';
import { Meta } from 'src/app/services/models/api';

@Injectable({
  providedIn: 'root'
})
export class AnalysisResolver implements Resolve<[Meta[]]> {
  constructor(private apiService: ApiService) {}
  resolve(route: ActivatedRouteSnapshot, state: RouterStateSnapshot): Observable<[Meta[]]> {
    return forkJoin([this.apiService.getMeta()]);
  }
}
