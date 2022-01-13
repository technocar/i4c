import { Component, ElementRef, OnInit, ViewChild } from '@angular/core';
import { ActivatedRoute, NavigationEnd, Router } from '@angular/router';
import { NgbDateStruct, NgbModal, NgbTimeStruct } from '@ng-bootstrap/ng-bootstrap';
import { BehaviorSubject } from 'rxjs';
import { filter } from 'rxjs/operators';
import { ApiService } from '../services/api.service';
import { AuthenticationService } from '../services/auth.service';
import { FiltersService } from '../services/filters.service';
import { Device, Tool, ToolUsage } from '../services/models/api';
import { DeviceType } from '../services/models/constants';
import { ToolDetailsComponent } from './tool-details/tool-details.component';

interface ToolsFilters {
  fdt: string,
  fd: string
}

@Component({
  selector: 'app-tools',
  templateUrl: './tools.component.html',
  styleUrls: ['./tools.component.scss']
})
export class ToolsComponent implements OnInit {

  @ViewChild("detail_dialog") detailDialog;
  @ViewChild("confirm_delete_dialog") confirmDeleteDialog;

  devices$: BehaviorSubject<Device[]> = new BehaviorSubject([]);
  tools$: BehaviorSubject<Tool[]> = new BehaviorSubject([]);
  toolUsageList$: BehaviorSubject<ToolUsage[]> = new BehaviorSubject([]);
  fetchingList$: BehaviorSubject<boolean> = new BehaviorSubject(false);

  filterDevice: string;
  filterDate: string;

  events: string[][] = [];
  selectedTool: Tool;
  access = {
    canDelete: false,
    canUpdate: false
  }
  headerCount = 7;

  constructor(
    private apiService: ApiService,
    private router: Router,
    private route: ActivatedRoute,
    private modalService: NgbModal,
    private filtersService: FiltersService,
    private authService: AuthenticationService
  )
  {
    this.access.canUpdate = authService.hasPrivilige("put/tools");
    this.access.canDelete = authService.hasPrivilige("delete/tools");
    if (!this.access.canUpdate)
      this.headerCount--;
    if (!this.access.canDelete)
      this.headerCount--;
    var filters: ToolsFilters = { fdt: undefined, fd: undefined };
    filtersService.read("tools", filters);
    this.filterDate = filters.fdt;
    this.filterDevice = filters.fd;
  }

  ngOnInit(): void {
    this.events = this.apiService.getToolEventTypes();
    this.apiService.getDevices()
      .subscribe(r => {
        this.devices$.next(r.filter((d) => [ DeviceType.Lathe, DeviceType.Mill ].indexOf(d.id) > -1));
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
    var filters: ToolsFilters = {
        fdt: this.filterDate ? this.filterDate : undefined,
        fd: (this.filterDevice ?? "") === "" ? undefined : this.filterDevice
     };
    this.filtersService.save("tools", filters);
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

  select(tool: Tool) {
    this.selectedTool = tool;
    this.modalService.open(this.detailDialog, { size: 'lg' });
  }

  new() {
    this.selectedTool = undefined;
    this.modalService.open(this.detailDialog, { size: 'lg' });
  }

  saveDetail(detail: ToolDetailsComponent) {
    detail.save().subscribe(r => {
      if (r) {
        this.modalService.dismissAll();
        this.getTools();
      }
    });
  }

  askForDelete(tool: Tool) {
    this.modalService.open(this.confirmDeleteDialog).result.then(r => {
      if (r === "delete")
        this.deleteTool(tool);
    });
  }

  deleteTool(tool: Tool) {
    this.apiService.deleteTool(tool)
      .subscribe(r => {
        this.getTools();
      },
      (err) => {
        alert(this.apiService.getErrorMsg(err));
      });
  }
}
