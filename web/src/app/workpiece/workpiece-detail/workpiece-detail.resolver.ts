import { Injectable } from '@angular/core';
import {
  Resolve,
  RouterStateSnapshot,
  ActivatedRouteSnapshot
} from '@angular/router';
import { Observable, of } from 'rxjs';
import { ApiService } from 'src/app/services/api.service';
import { WorkPiece } from 'src/app/services/models/api';

@Injectable({
  providedIn: 'root'
})
export class WorkpieceDetailResolver implements Resolve<WorkPiece> {

  constructor(private apiService: ApiService) {
  }

  resolve(route: ActivatedRouteSnapshot, state: RouterStateSnapshot): Observable<WorkPiece> {
    return this.apiService.getWorkPiece(route.paramMap.get('id'), true);
  }
}
