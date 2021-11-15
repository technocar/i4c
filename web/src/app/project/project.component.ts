import { Component, OnInit } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { BehaviorSubject } from 'rxjs';
import { ApiService } from '../services/api.service';
import { Project, ProjectInstall, ProjectInstallParams, ProjectInstallStatus } from '../services/models/api';
import { NotificationService } from '../services/notification.service';

@Component({
  selector: 'app-project',
  templateUrl: './project.component.html',
  styleUrls: ['./project.component.scss']
})
export class ProjectComponent implements OnInit {

  private _projects: Project[] = [];
  selectedProject: string = '';
  selectedVersion: string = '';
  fromDate: Date;
  toDate: Date;
  projects$: BehaviorSubject<string[]> = new BehaviorSubject([]);
  versions$: BehaviorSubject<string[]> = new BehaviorSubject([]);
  installed$: BehaviorSubject<ProjectInstall[]> = new BehaviorSubject([]);

  constructor(
    private apiService: ApiService,
    private notifService: NotificationService,
    private route: ActivatedRoute) {
    let now = new Date();
    this.fromDate = new Date(Date.UTC(now.getFullYear(), now.getMonth(), 1, 0, 0, 0, 0));
    this.toDate = new Date(Date.UTC(now.getFullYear(), now.getMonth() + 1, 0, 0, 0, 0, 0));
  }

  ngOnInit(): void {
    this.route.data.subscribe((r: any) => {
        this._projects = r.data;
        this.projects$.next(this._projects.map((p) => { return p.name }));
      });
    this.getInstalledProjects();
  }

  projectSelectionChanged() {
    this.getVersions(this.selectedProject);
    this.getInstalledProjects();
  }

  getVersions(projectName: string) {
    this.selectedVersion = '';
    var project = this._projects.find((p) => { return p.name === projectName });
    this.versions$.next(project ? project.versions : []);
  }

  getInstalledProjects() {
    let params: ProjectInstallParams = {
      project_name: this.selectedProject === '' ? undefined : this.selectedProject,
      before: this.toDate,
      after: this.fromDate
    }
    this.apiService.getInstalledProjects(params)
      .subscribe(r => {
        this.installed$.next(r);
      })
  }

  install(name: string, version: string) {
    if (!name) {
      alert("Projekt nincs kiválasztva!");
      return;
    }
    if (!version) {
      alert("Verzió nincs kiválasztva!");
      return;
    }

    this.apiService.getInstalledProjects({
      status: ProjectInstallStatus.Working
    }).subscribe(r => {
      if (r.length === 0) {
        this.apiService.installProject(name, version)
          .subscribe((r) => {
            alert(`A ${name} ${version} sikeresen telepítve`);
            this.getInstalledProjects();
          }, (err) => {
            alert(this.apiService.getErrorMsg(err));
          });
      } else {
        alert("Van futó telepítés!");
      }
    }, err => {
      alert(this.apiService.getErrorMsg(err));
    })
  }

  filterChanged() {
    this.getInstalledProjects();
  }

  convertToDate(value: string) {
    return new Date(value);
  }

  notifTest() {
    this.notifService.sendDesktopNotif("I4C", "test message");
  }
}
