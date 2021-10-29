import { Injectable } from '@angular/core';
import { HttpRequest, HttpHandler, HttpEvent, HttpInterceptor, HttpErrorResponse } from '@angular/common/http';
import { Observable, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { AuthenticationService } from './auth.service';
import { Router } from '@angular/router';

@Injectable()
export class AuthenticationInterceptor implements HttpInterceptor {

  constructor(
    private authService: AuthenticationService,
    private router: Router
  ) {
  }

  intercept(request: HttpRequest<any>, next: HttpHandler): Observable<HttpEvent<any>> {
    request = this.addAuth(request);

    return next.handle(request).pipe(catchError((err: HttpErrorResponse, caught: Observable<any>) => {
      return throwError(err);
    }));
  }

  private addAuth(request: HttpRequest<any>): HttpRequest<any> {
    const isApiUrl = true;//this.isSameOriginUrl(request);
    if (isApiUrl) {
      if (this.authService.isAuthenticated())
        this.authService.extendExpiration();
      else
        this.router.navigate(['/login']);
      return request = request.clone({
        setHeaders: {
          "Authorization": `Basic ${this.authService.currentUserValue.token}`
        }
      });
    } else {
      return request;
    }
  }

  private isSameOriginUrl(req: any) {
    // It's an absolute url with the same origin.
    if (req.url.startsWith(`${window.location.origin}/`)) {
      return true;
    }

    // It's a protocol relative url with the same origin.
    // For example: //www.example.com/api/Products
    if (req.url.startsWith(`//${window.location.host}/`)) {
      return true;
    }

    // It's a relative url like /api/Products
    if (/^\/[^\/].*/.test(req.url)) {
      return true;
    }

    // It's an absolute or protocol relative url that
    // doesn't have the same origin.
    return false;
  }
}
