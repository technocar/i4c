import { Component, Input, OnInit, ViewChild } from '@angular/core';
import { NgForm } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { BehaviorSubject, Observable } from 'rxjs';
import { ApiService } from 'src/app/services/api.service';
import { AuthenticationService } from 'src/app/services/auth.service';
import { AlarmNotificationType, AlarmSubscription, AlarmSubscriptionChange, AlarmSubscriptionGroupGrant } from 'src/app/services/models/api';
import { Labels } from 'src/app/services/models/constants';
import { AppNotifType, NotificationService } from 'src/app/services/notification.service';

interface SubsGroup {
  id: string,
  selected: boolean
}

@Component({
  selector: 'app-subscription-detail',
  templateUrl: './detail.component.html',
  styleUrls: ['./detail.component.scss']
})
export class AlarmSubscriptionDetailComponent implements OnInit {

  @ViewChild("#save") saveButton: HTMLInputElement;
  @Input() embed: boolean = false;

  private _saved: BehaviorSubject<boolean> = new BehaviorSubject(false);

  subs: AlarmSubscription;
  groups: SubsGroup[] = [];
  methods = Labels.alarm.methods;
  own: boolean = true;
  isNew: boolean = false;

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private authService: AuthenticationService,
    private apiService: ApiService,
    private notifService: NotificationService
  ) {}

  ngOnInit(): void {
    this.route.data.subscribe(r => {
      this.subs = r.data[0];
      this.subs.groups = this.subs.groups ?? [];
      var userGroups = (r.data[1] as AlarmSubscriptionGroupGrant[]) ?? [];
      if (userGroups.length > 0) {
        this.groups = userGroups[0].groups.map(g => <SubsGroup>{id: g, selected: this.subs.groups.indexOf(g) > -1});
      }
      console.log(this.groups);
      this.own = this.subs.user === this.authService.currentUserValue.id;
      this.isNew = (this.subs.id ?? -1) === -1;
      if (this.isNew)
        this.subs.address_name = '';
    });
  }


  submit(form: NgForm) {
    if (!form.valid) {
      this._saved.next(false);
      return;
    }
    this.ensurePushSubscription()
      .subscribe(() => {
        this.doSave();
      }, err => {
        this.notifService.sendAppNotif(AppNotifType.Error, this.apiService.getErrorMsg(err).toString());
      });
  }

  save(): Observable<boolean> {
    return new Observable<boolean>(observer => {
      this._saved.subscribe(r => {
        observer.next(r);
        observer.complete();
      }, err => {
        observer.error(err);
        observer.complete();
      });
      this.saveButton.click();

      return {
        unsubscribe() {}
      };
    });
  }

  ensurePushSubscription(): Observable<void> {
    return new Observable(observer => {
      if (this.subs.method === AlarmNotificationType.Push) {
        this.apiService.getSetting("push_public_key").subscribe(value => {
          this.notifService.subscribeToPushNotif(value, true).subscribe(subscription => {
            this.subs.address = JSON.stringify(subscription.toJSON());
            observer.next();
            observer.complete();
          }, err => {
            observer.error(err);
            observer.complete();
          });
        }, err => {
          observer.error(err);
          observer.complete();
        });
      } else {
        observer.next();
        observer.complete();
      }

      return {
        unsubscribe() {
        }
      };
    })
  }

  doSave() {
    if (this.isNew) {
      this.subs.id = undefined;
      this.subs.groups = this.groups.filter(g => g.selected).map(g => g.id);
      this.apiService.addAlarmSubscription(this.subs)
        .subscribe((r) => {
          this.subs.id = r.id;
          this._saved.next(true);
          if (!this.embed)
            this.router.navigate([r.user, r.id], { relativeTo: this.route.parent, replaceUrl: true });
          this.notifService.sendAppNotif(AppNotifType.Success, "Feliratkozva!");
        }, err => {
          this._saved.next(false);
          this.notifService.sendAppNotif(AppNotifType.Error, this.apiService.getErrorMsg(err).toString());
        });
    } else {
      let changes: AlarmSubscriptionChange = {
        status: this.subs.status,
        address: this.subs.address,
        address_name: this.subs.address_name,
        clear_address: (this.subs.address ?? "") === "",
        clear_address_name: (this.subs.address_name ?? "") === "",
        set_groups: this.groups.filter(g => g.selected).map(g => g.id)
      };
      this.apiService.updateAlarmSubscription(this.subs.id, {
        conditions: [],
        change: changes
      }).subscribe(r => {
        this._saved.next(r.changed);
        if (!this.embed)
          this.router.navigate([this.subs.address_name, this.subs.id], { relativeTo: this.route.parent, replaceUrl: true });
        this.notifService.sendAppNotif(AppNotifType.Success, "Sikeresen módosítás!");
      }, err => {
        this._saved.next(false);
        this.notifService.sendAppNotif(AppNotifType.Error, this.apiService.getErrorMsg(err).toString());
      });
    }
  }

  methodChange(method) {
    this.subs.method = method;
  }

  statusChange(status) {
    this.subs.status = status;
  }

  ngOnDestroy() {

  }
}
