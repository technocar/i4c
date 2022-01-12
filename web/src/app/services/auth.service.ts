import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject, Observable } from 'rxjs';

import { Router } from '@angular/router';
import { ApiService, LoginResponse } from './api.service';
import { DeviceType } from './models/constants';
import { User, UserPrivilige } from './models/api';
import { map, tap } from 'rxjs/operators';

export class AuthenticatedUser {
  id: string;
  username: string;
  token: string;
  expires: number;
  privs: UserPrivilige[]
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
    return this.api.login(username, password).pipe(
      tap(user => {
        this.storeUser({
          id: user.id,
          username: user.login_name,
          expires: Date.now() + (1000 * 60 * 45),
          token: `${window.btoa(username + ':' + password)}`,
          privs: user.privs ?? []
        });
      })
    );
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

  hasPrivilige(endpoint: string, privilige?: string): boolean {
    if (!this.isAuthenticated())
      return false;

    var privs = this.currentUserValue?.privs ?? [];
    return (privs.find((p) => p.endpoint === endpoint && ((p.features ?? []).length === 0 || p.features.indexOf(privilige) > -1 ))) !== undefined;
  }
}
