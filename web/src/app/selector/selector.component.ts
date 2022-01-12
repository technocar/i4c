import { Component, OnInit } from '@angular/core';
import { Router } from '@angular/router';
import { AuthenticationService } from '../services/auth.service';

@Component({
  selector: 'app-selector',
  templateUrl: './selector.component.html',
  styleUrls: ['./selector.component.scss']
})
export class SelectorComponent implements OnInit {

  access = {
    dashboard: false,
    alarms: false,
    tools: false,
    projects: false,
    analyses: false,
    workpieces: false
  }

  constructor(
    private router: Router,
    private authService: AuthenticationService
  ) {
    this.access.dashboard = authService.hasPrivilige("get/log/snapshot");
    this.access.projects = authService.hasPrivilige("get/projects");
    this.access.tools = authService.hasPrivilige("get/tools");
    this.access.workpieces = authService.hasPrivilige("get/workpiece");
    this.access.alarms = authService.hasPrivilige("get/alarm/defs");
    this.access.analyses = authService.hasPrivilige("get/stat/def");
  }

  ngOnInit(): void {

  }

  load(device: string) {
    this.router.navigate(["/dashboard"], { queryParams: { device: device } });
  }

}
