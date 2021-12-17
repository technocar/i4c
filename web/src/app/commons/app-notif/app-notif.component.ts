import { Component, OnInit } from '@angular/core';
import { BehaviorSubject } from 'rxjs';
import { AppNotif, AppNotifType, NotificationService } from 'src/app/services/notification.service';

@Component({
  selector: 'app-notif',
  templateUrl: './app-notif.component.html',
  styleUrls: ['./app-notif.component.scss']
})
export class AppNotifComponent implements OnInit {

  notifs$: BehaviorSubject<AppNotif[]> = new BehaviorSubject([]);

  constructor(
    private notifService: NotificationService
  ) { }

  ngOnInit(): void {
    this.notifService.receiveAppNotif.subscribe(n => {
      var notifs = this.notifs$.value;
      n.id = ((notifs ?? []).length === 0 ? 0 : Math.max(...notifs.map(n => n.id))) + 1,
      notifs.push(n);
      this.notifs$.next(notifs);
      if (n.autoClose)
        setTimeout(() => {
          this.remove(n);
        }, 3000);
    })
  }

  remove(notif: AppNotif) {
    var notifs = this.notifs$.value;
    var idx = notifs.findIndex(n => n.id === notif.id);
    if (idx === -1)
      return;
    notifs.splice(idx, 1);
    this.notifs$.next(notifs);
  }

}
