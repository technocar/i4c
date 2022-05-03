import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject, Observable } from 'rxjs';

import { Router } from '@angular/router';
import { User, UserPrivilige } from './models/api';

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
  private _isAuthenticated = false;

  constructor(private http: HttpClient, private router: Router) {
    this.currentUserSubject = new BehaviorSubject<AuthenticatedUser>(JSON.parse(localStorage.getItem('current_user')));
    this.currentUser = this.currentUserSubject.asObservable();
  }

  public get currentUserValue(): AuthenticatedUser {
    return this.currentUserSubject.value;
  }

  public isAuthenticated(): boolean {
    const expired = !!this.currentUserValue && !!this.currentUserValue.expires && this.currentUserValue.expires > Date.now();
    if (expired != this._isAuthenticated) {
      this._isAuthenticated = expired;
      this.currentUserSubject.next(JSON.parse(localStorage.getItem('current_user')));
    }
    return expired;
  }

  login(username: string, password: string, user: User): User {
    this.storeUser({
      id: user.id,
      username: user.login_name,
      expires: Date.now() + (1000 * 60 * 45),
      token: `${window.btoa(username + ':' + password)}`,
      privs: user.privs ?? []
    });
    return user;
  }

  lastLoggedUserName(): string {
    return localStorage.getItem('last_logged_user_name');
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
    localStorage.setItem('last_logged_user_name', user.username);
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
    return (privs.find((p) => p.endpoint === endpoint && (!privilige || p.features.indexOf(privilige) > -1))) !== undefined;
  }
}
