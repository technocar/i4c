import { Component, OnInit } from '@angular/core';
import { versions } from 'process';
import { BehaviorSubject } from 'rxjs';
import { ApiService } from '../services/api.service';
import { Project } from '../services/models/api';

@Component({
  selector: 'app-project',
  templateUrl: './project.component.html',
  styleUrls: ['./project.component.scss']
})
export class ProjectComponent implements OnInit {

  private _projects: Project[] = [];
  projects$: BehaviorSubject<string[]> = new BehaviorSubject([]);
  versions$: BehaviorSubject<string[]> = new BehaviorSubject([]);

  constructor(private apiService: ApiService) {
    apiService.getProjects()
      .subscribe((r) => {
        this._projects = r;
        this.projects$.next(this._projects.map((p) => { return p.name }));
      });
  }

  ngOnInit(): void {
  }

  getVersions(projectName: string) {
    var project = this._projects.find((p) => { return p.name === projectName });
    this.versions$.next(project ? project.versions : []);
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

    this.apiService.installProject(name, version)
      .subscribe((r) => {
        alert("Telepítve!");
      }, (err) => {
        alert(this.apiService.getErrorMsg(err));
      });
  }
}
