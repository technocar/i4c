import { Component, OnInit } from '@angular/core';
import { BehaviorSubject } from 'rxjs';
import { ApiService } from 'src/app/services/api.service';
import { AuthenticationService } from 'src/app/services/auth.service';
import { AlarmSubscription } from 'src/app/services/models/api';
import { Labels } from 'src/app/services/models/constants';
import { AppNotifType, NotificationService } from 'src/app/services/notification.service';

@Component({
  selector: 'app-subscription',
  templateUrl: './subscription.component.html',
  styleUrls: ['./subscription.component.scss']
})
export class AlarmSubscriptionComponent implements OnInit {

  subs$: BehaviorSubject<AlarmSubscription[]> = new BehaviorSubject([]);
  loading$: BehaviorSubject<boolean> = new BehaviorSubject(false);
  users$: BehaviorSubject<[string, string][]> = new BehaviorSubject([]);
  selectedUser: string;

  constructor(
    private apiService: ApiService,
    private notifService: NotificationService,
    private authService: AuthenticationService) { }

  ngOnInit(): void {
    this.apiService.getUsers(false)
      .subscribe(users => {
        this.users$.next(users.map(u => <[string, string]>[u.id, u.name]));
        this.selectedUser = this.authService.currentUserValue.id;
        this.getSubscriptions();
      })
  }

  getSubscriptions() {
    this.loading$.next(true);
    try {
    this.apiService.getAlarmSubscriptions({
      user: (this.selectedUser ?? "") === "" ? this.authService.currentUserValue.id : this.selectedUser
    })
      .subscribe(r => {
        this.subs$.next(r);
      },
      err => {
        this.notifService.sendAppNotif(AppNotifType.Error, this.apiService.getErrorMsg(err).toString());
      },
      () => {
        this.loading$.next(false);
      }
    );
    } catch(err) {
      this.loading$.next(false);
      this.notifService.sendAppNotif(AppNotifType.Error, this.apiService.getErrorMsg(err).toString());
    }
  }

  trackById(index: number, sub: AlarmSubscription): number {
    return sub.id;
  }

  getMethodCaption(code: string): string {
    var caption = Labels.alarm.methods.find(m => m[0] === code);
    if (!caption)
      return code;

    return caption[1];
  }
}
