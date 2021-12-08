import { Component, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { NgbDate, NgbDateStruct } from '@ng-bootstrap/ng-bootstrap';
import { BehaviorSubject } from 'rxjs';
import { ApiService } from '../services/api.service';
import { Project, ProjectInstall, ProjectInstallParams, ProjectInstallStatus, ProjectStatus } from '../services/models/api';
import { NotificationService } from '../services/notification.service';

@Component({
  selector: 'app-project',
  templateUrl: './project.component.html',
  styleUrls: ['./project.component.scss']
})
export class ProjectComponent implements OnInit {

  private _projects: Project[] = [];
  private _filterFromDate: NgbDateStruct;
  private _filterToDate: NgbDateStruct;

  selectedProject: string = '';
  selectedVersion: string = '';

  get filterFromDate(): NgbDateStruct { return this._filterFromDate; }
  set filterFromDate(value: NgbDateStruct) { this._filterFromDate = value; this.filter(); }
  get filterToDate(): NgbDateStruct { return this._filterToDate; }
  set filterToDate(value: NgbDateStruct) { this._filterToDate = value; this.filter(); }
  filterProject: string;
  filterVersion: number;
  filterStatus: string;

  projects$: BehaviorSubject<string[]> = new BehaviorSubject([]);
  versions$: BehaviorSubject<string[]> = new BehaviorSubject([]);
  installed$: BehaviorSubject<ProjectInstall[]> = new BehaviorSubject([]);
  fetchingList$: BehaviorSubject<boolean> = new BehaviorSubject(false);
  statuses: string[][] = [
    ["", " - "],
    ["todo", $localize `:@@install_status_todo:Várakozik`],
    ["working", $localize `:@@install_status_working:Folyamatban`],
    ["done", $localize `:@@install_status_done:Kész`],
    ["fail", $localize `:@@install_status_fail:Sikeretelen`]
  ];

  constructor(
    private apiService: ApiService,
    private notifService: NotificationService,
    private route: ActivatedRoute,
    private router: Router) {
    let now = new Date();
    this._filterFromDate = { year: now.getFullYear(), month: now.getMonth() + 1, day: 1 };
    now = new Date(now.getFullYear(), now.getMonth() + 1, 0);
    this._filterToDate = { year: now.getFullYear(), month: now.getMonth() + 1, day: now.getDate() };

    let qpds = route.snapshot.queryParamMap.get("fds");
    let qpde = route.snapshot.queryParamMap.get("fde");
    if (qpds || qpde) {
      this._filterFromDate = this.convertFromDate(qpds);
      this._filterToDate = this.convertFromDate(qpde);
    }
    this.filterProject = route.snapshot.queryParamMap.get("fp");
    this.filterVersion = parseInt(route.snapshot.queryParamMap.get("fv"));
    this.filterVersion = isNaN(this.filterVersion) ? undefined : this.filterVersion;
    this.filterStatus = route.snapshot.queryParamMap.get("fs");
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
  }

  getVersions(projectName: string) {
    this.selectedVersion = '';
    var project = this._projects.find((p) => { return p.name === projectName });
    this.versions$.next(project ? project.versions : []);
  }

  getInstalledProjects() {
    let params: ProjectInstallParams = {
      project_name: (this.filterProject ?? "") === "" ? undefined : this.filterProject,
      after: this.convertToDate(this.filterFromDate),
      before: this.convertToDate(this.filterToDate),
      ver: (this.filterVersion ?? "") === "" ? undefined : this.filterVersion,
      status: (this.filterStatus ?? "") === "" ? undefined : this.filterStatus as ProjectInstallStatus
    }
    this.fetchingList$.next(true);
    this.apiService.getInstalledProjects(params)
      .subscribe(r => {
        this.installed$.next(r);
      },
      (err) => {},
      () => {
        this.fetchingList$.next(false);
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

  filter() {
    this.router.navigate([], {
      relativeTo: this.route,
      queryParams: {
        fds: this.filterFromDate ? `${this.filterFromDate.year}-${this.filterFromDate.month}-${this.filterFromDate.day}` : undefined,
        fde: this.filterToDate ? `${this.filterToDate.year}-${this.filterToDate.month}-${this.filterToDate.day}` : undefined,
        fp: (this.filterProject ?? "") === "" ? undefined : this.filterProject,
        fv: (this.filterVersion ?? "") === "" ? undefined : this.filterVersion,
        fs: (this.filterStatus ?? "") === "" ? undefined : this.filterStatus
      },
      queryParamsHandling: 'merge'
    });
    this.getInstalledProjects();
  }

  convertToDate(value: NgbDateStruct): Date {
    if (value)
      return new Date(Date.UTC(value.year, value.month - 1, value.day));
    else
      return undefined;
  }

  convertFromDate(value: string): NgbDateStruct {
    if (!value)
      return undefined;

    try
    {
      let date = new Date(value);
      return { year: date.getFullYear(), month: date.getMonth() + 1, day: date.getDate() };
    }
    catch
    {
      console.error(`Invalid Date "${value}" is invalid`);
      return undefined;
    }
  }

  notifTest() {
    this.notifService.sendDesktopNotif("I4C", "test message");
  }

  getStatusDesc(code: string): string {
    var status = this.statuses.find((s) => { return s[0] === code });
    if (status)
      return status[1];
    else
      return code;
  }
}
