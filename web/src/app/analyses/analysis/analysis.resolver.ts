import { Injectable } from '@angular/core';
import {
  Router, Resolve,
  RouterStateSnapshot,
  ActivatedRouteSnapshot,
  ActivatedRoute
} from '@angular/router';
import { forkJoin, Observable, of } from 'rxjs';
import { ApiService } from 'src/app/services/api.service';
import { Meta, StatDef } from 'src/app/services/models/api';

@Injectable({
  providedIn: 'root'
})
export class AnalysisResolver implements Resolve<[StatDef, Meta[], string[], string]> {
  constructor(
    private apiService: ApiService) {}

  resolve(route: ActivatedRouteSnapshot, state: RouterStateSnapshot): Observable<[StatDef, Meta[], string[], string]> {
    return this.apiService.getAnalysisData(route.paramMap.get("id"), route.paramMap.get("type"), route.paramMap.get("caption"));
  }
}
