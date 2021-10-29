import { Injectable } from '@angular/core';
import { Router, CanActivate, ActivatedRouteSnapshot, RouterStateSnapshot } from '@angular/router';
import { HttpRequest, HttpHandler, HttpEvent, HttpInterceptor, HttpErrorResponse } from '@angular/common/http';
import { Observable, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';

import { AuthenticationService } from './auth.service';

@Injectable({ providedIn: 'root' })
export class AuthGuard implements CanActivate, HttpInterceptor  {
  constructor(
    private router: Router,
    private authenticationService: AuthenticationService
  ) { }

  canActivate(route: ActivatedRouteSnapshot, state: RouterStateSnapshot) {
    if (this.authenticationService.isAuthenticated()) {
      return true;
    }

    // not logged in so redirect to login page with the return url
    this.router.navigate(['/login'], { queryParams: { returnUrl: state.url } });
    return false;
  }

  intercept(request: HttpRequest<any>, next: HttpHandler): Observable<HttpEvent<any>> {
    return next.handle(request).pipe(catchError((err: HttpErrorResponse, caught: Observable<any>) => {
      if (err.status === 401) {
        // auto logout if 401 response returned from api
        this.authenticationService.logout();
        location.reload();
      }

      const error = err.error.message || err.statusText;
      return throwError(error);
    }))
  }
}
