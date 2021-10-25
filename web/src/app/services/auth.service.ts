import { Injectable, Inject } from '@angular/core';
import { HttpRequest, HttpHandler, HttpEvent, HttpInterceptor, HttpErrorResponse, HttpClient } from '@angular/common/http';
import { BehaviorSubject, Observable, throwError, Subject } from 'rxjs';
import { catchError, map, switchMap, tap } from 'rxjs/operators';

import { Router } from '@angular/router';
import { ApiService } from './api.service';
import { DeviceType } from './models/constants';
import { User } from './models/api';

export class AuthenticatedUser {
  id: string;
  username: string;
  token: string;
  expires: number;
}

@Injectable({ providedIn: 'root' })
export class AuthenticationService {
  private currentUserSubject: BehaviorSubject<AuthenticatedUser>;
  public currentUser: Observable<AuthenticatedUser>;

  constructor(private http: HttpClient, private router: Router, private api: ApiService) {
    this.currentUserSubject = new BehaviorSubject<AuthenticatedUser>(JSON.parse(localStorage.getItem('current_user')));
    this.currentUser = this.currentUserSubject.asObservable();
  }

  public get currentUserValue(): AuthenticatedUser {
    return this.currentUserSubject.value;
  }

  public isAuthenticated(): boolean {
    return !!this.currentUserValue && !!this.currentUserValue.expires && this.currentUserValue.expires > Date.now();
  }

  login(username: string, password: string): Observable<User> {
    this.storeUser({
      id: username,
      username: username,
      expires: Date.now() + (1000 * 60 * 45),
      token: `${window.btoa(username + ':' + password)}`
    });

    return this.api.login();
  }

  removeUser() {
    localStorage.removeItem('current_user');
    this.currentUserSubject.next(null);
  }

  logout() {
    this.removeUser();
    this.router.navigate(['/login']);
  }

  storeUser(user: AuthenticatedUser) {
    localStorage.setItem('current_user', JSON.stringify(user));
    this.currentUserSubject.next(user);
  }

  extendExpiration() {
    if (this.isAuthenticated()) {
      this.currentUserValue.expires = Date.now() + (1000 * 60 * 45);
      this.storeUser(this.currentUserValue);
    }
  }
}
