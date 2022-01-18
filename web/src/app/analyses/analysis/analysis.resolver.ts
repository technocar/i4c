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
import { AnalysisType } from '../analyses.component';

@Injectable({
  providedIn: 'root'
})
export class AnalysisResolver implements Resolve<[StatDef, Meta[]]> {
  constructor(
    private apiService: ApiService) {}

  resolve(route: ActivatedRouteSnapshot, state: RouterStateSnapshot): Observable<[StatDef, Meta[]]> {
    return this.apiService.getAnalysisData(route.paramMap.get("id"), route.paramMap.get("type"));
  }
}
