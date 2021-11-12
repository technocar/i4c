import { Component } from '@angular/core';
import { NavigationCancel, NavigationEnd, NavigationError, NavigationStart, Router } from '@angular/router';
import { ApiService, Download, DownloadState } from './services/api.service';
import { DownloadService } from './services/download.service';

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.sass']
})
export class AppComponent {
  title = 'webmonitor';
  loading: boolean = false;
  downloading: boolean = false;
  downloadError: boolean = false;
  downloadErrorMsg: string = "";
  downloadProgress: number = 0;

  constructor(
    private router: Router,
    private downloadService: DownloadService,
    private apiService: ApiService
  ) {
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

  cancelDownload() {
    this.downloadService.cancelDownload();
    this.downloading = false;
    this.downloadProgress = 0;
  }
}
