import { Component, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { NgbDateStruct, NgbTimeStruct } from '@ng-bootstrap/ng-bootstrap';
import { BehaviorSubject } from 'rxjs';
import { ApiService } from '../services/api.service';
import { Device, Tool, ToolUsage } from '../services/models/api';
import { DeviceType } from '../services/models/constants';

@Component({
  selector: 'app-tools',
  templateUrl: './tools.component.html',
  styleUrls: ['./tools.component.scss']
})
export class ToolsComponent implements OnInit {

  devices$: BehaviorSubject<Device[]> = new BehaviorSubject([]);
  tools$: BehaviorSubject<Tool[]> = new BehaviorSubject([]);
  toolUsageList$: BehaviorSubject<ToolUsage[]> = new BehaviorSubject([]);
  fetchingList$: BehaviorSubject<boolean> = new BehaviorSubject(false);

  filterDevice: string;
  filterDate: string;

  events: string[][] = [
    ["install_tool", $localize `:@@tools_event_install_tool:Beszerelés`],
    ["remove_tool", $localize `:@@tools_event_remove_tool:Kiszerelés`]
  ]

  constructor(
    private apiService: ApiService,
    private router: Router,
    private route: ActivatedRoute)
  {
    this.filterDate = route.snapshot.queryParamMap.get("fdt");
    this.filterDevice = route.snapshot.queryParamMap.get("fd");
  }

  ngOnInit(): void {
    this.apiService.getDevices()
      .subscribe(r => {
        this.devices$.next(r);
        if (!this.filterDevice)
          this.filterDevice = r[0].id;
        this.getTools();
      });
    this.getToolUsageList();
  }

  getTools() {
    this.fetchingList$.next(true);
    this.apiService.getTools({
      device: this.filterDevice as DeviceType,
      timestamp: (this.filterDate ?? "") === "" ? undefined : new Date(this.filterDate)
    })
      .subscribe(r => {
        this.tools$.next(r);
      },
      (err) => {},
      () => {
        this.fetchingList$.next(false);
      });
  }

  getToolUsageList() {
    this.apiService.getToolUsageList()
      .subscribe(r => {
        this.toolUsageList$.next(r);
      })
  }

  filter() {
    this.router.navigate([], {
      relativeTo: this.route,
      queryParams: {
        fdt: this.filterDate ? this.filterDate : undefined,
        fd: (this.filterDevice ?? "") === "" ? undefined : this.filterDevice
      },
      queryParamsHandling: 'merge'
    });
    this.getTools();
  }

  getDeviceName(id: string): string {
    var device = this.devices$.value.find((d) => { return d.id === id });
    if (device)
      return device.name;
    else
      return id;
  }

  getEventName(code: string): string {
    var event = this.events.find((e) => { return e[0] === code });
    if (event)
      return event[1];
    else
      return code;
  }
}
