import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject, Observable } from 'rxjs';

import { Router } from '@angular/router';
import { ApiService, LoginResponse } from './api.service';
import { DeviceType } from './models/constants';
import { User } from './models/api';
import { map, tap } from 'rxjs/operators';

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
    return this.api.login(username, password).pipe(
      tap(r => {
        this.storeUser({
          id: r.user.id,
          username: r.user.login_name,
          expires: Date.now() + (1000 * 60 * 45),
          token: `${window.btoa(username + ':' + password)}`
        });
      }),
      map(r => {
        return r.user;
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
}
