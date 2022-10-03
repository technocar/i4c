import { Component, OnInit } from '@angular/core';
import { NavigationCancel, NavigationEnd, NavigationError, NavigationStart, Router } from '@angular/router';
import { SwUpdate } from '@angular/service-worker';
import { BehaviorSubject, Observable } from 'rxjs';
import { environment } from 'src/environments/environment';
import { ApiService, Download, DownloadState } from './services/api.service';
import { AuthenticationService } from './services/auth.service';
import { Breadcrumb, BreadcrumbService } from './services/breadcrumb.service';
import { DownloadService } from './services/download.service';

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.sass']
})
export class AppComponent implements OnInit {
  title = 'webmonitor';
  loading: boolean = false;
  downloading: boolean = false;
  downloadError: boolean = false;
  downloadErrorMsg: string = "";
  downloadProgress: number = 0;
  loggedUserName$: BehaviorSubject<string> = new BehaviorSubject("");
  isLoggedIn$: BehaviorSubject<boolean> = new BehaviorSubject(false);
  breadcrumbs$: Observable<Breadcrumb[]>;
  access = {
    subscriptions: false
  }
  appVersion = environment.appVersion;

  constructor(
    private router: Router,
    private downloadService: DownloadService,
    private apiService: ApiService,
    private authService: AuthenticationService,
    private breadcrumbService: BreadcrumbService,
    private swUpdate: SwUpdate
  ) {
    authService.currentUser.subscribe(r => {
      this.access.subscriptions = authService.hasPrivilige("get/alarm/subs");
      if (r && authService.isAuthenticated()) {
        this.loggedUserName$.next(r.username);
        this.isLoggedIn$.next(true);
      } else {
        this.isLoggedIn$.next(false);
        this.loggedUserName$.next("");
      }
    });
    this.router.events.subscribe(ev => {
      if (ev instanceof NavigationStart) {
        this.loading = true;
      }
      if (
        ev instanceof NavigationEnd ||
        ev instanceof NavigationCancel ||
        ev instanceof NavigationError
      ) {
        this.loading = false;
      }
    });

    this.breadcrumbs$ = breadcrumbService.breadcrumbs$;

    downloadService.subscribe(
      (d: Download) => {
        if (d.state === DownloadState.InProgress) {
          if (this.downloadError)
            this.downloadError = false;
          if (!this.downloading) {
            this.downloading = true;
            this.downloadProgress = 0;
          }
          this.downloadProgress = d.progress;
        } else if (d.state === DownloadState.Done) {
          this.downloading = false;
        }
      },
      (err) => {
        if (this.downloadError)
          this.downloadError = true;
        this.downloadErrorMsg = apiService.getErrorMsg(err).toString();
      }
    );
  }

  ngOnInit(): void {
    if (this.swUpdate.isEnabled) {
      this.swUpdate.available
      .subscribe(e => {
        console.info(e);
        if (e.available) {
          console.info(`currentVersion=[${e.current}`);
        }
      });
    }
  }

  cancelDownload() {
    this.downloadService.cancelDownload();
    this.downloading = false;
    this.downloadProgress = 0;
  }

  logout() {
    this.authService.logout();
  }
}
