import { HttpErrorResponse } from '@angular/common/http';
import { Component, OnInit, ViewChild } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { NgbDateStruct, NgbTimeStruct } from '@ng-bootstrap/ng-bootstrap';
import { BehaviorSubject, forkJoin, Observable, Subscription } from 'rxjs';
import { tap } from 'rxjs/operators';
import { MetaFilterComponent, MetricFilterModel } from '../commons/meta-filter/meta-filter.component';
import { ApiService } from '../services/api.service';
import { Category, EventLog, EventValues, FindParams, ListItem, Meta, Snapshot } from '../services/models/api';
import { DeviceType } from '../services/models/constants';

@Component({
  selector: 'app-dashboard',
  templateUrl: './dashboard.component.html',
  styleUrls: ['./dashboard.component.scss']
})
export class DashboardComponent implements OnInit {

  @ViewChild("searchDialog") searchDialog: MetaFilterComponent;

  _currentDate: NgbDateStruct;
  _currentTime: NgbTimeStruct;

  _lastListTimestamp: number = 0;
  _stopped: boolean;

  isDataLoaded: boolean = false;
  isEventDataLoaded: boolean = false;
  isListMode: boolean = false;
  listWindow: number = 20;

  get currentDate(): NgbDateStruct {
    return this._currentDate;
  }
  set currentDate(value: NgbDateStruct) {
    this._currentDate = value;
    this.setDate(this._currentDate);
  }
  get currentTime(): NgbTimeStruct {
    return this._currentTime;
  }
  set currentTime(value: NgbTimeStruct) {
    this._currentTime = value;
    this.setTime(this._currentTime);
  }

  private _updateIntervalTimeNormal = 1000;
  private _updateIntervalTimeFast = 4000;
  private _updateIntervalTimeCurrent: number = 1000;
  private _updateInterval;
  private _metaList: Meta[] = [];
  private _allEventValues: EventValues[] = [];
  private _activeSnapshotRequest: Subscription;
  private _activeListRequest: Subscription;

  isAutoMode: boolean = true;
  noData: boolean = false;
  snapshot: Snapshot;
  private _device: DeviceType;
  public get device(): DeviceType {
    return this._device;
  }
  public set device(value: DeviceType) {
    this._device = value;
    this.getMetaListOfDevice();
  }
  timestamp: number;
  backwardTime: number = 30; //in seconds
  forwardTime: number = 30; //in seconds

  events$: BehaviorSubject<EventLog[]> = new BehaviorSubject([]);
  list$: BehaviorSubject<ListItem[]> = new BehaviorSubject([]);

  metaListOfDevice: Meta[] = [];

  constructor(
    private apiService: ApiService,
    private route: ActivatedRoute
  ) {
    this.setTimestamp(this.getCurrentDate());
    this.device = DeviceType.Lathe;
    let pDev = this.route.snapshot.queryParamMap.get('device');
    if (pDev)
      this.device = pDev as DeviceType;
  }

  ngOnInit(): void {
    forkJoin([this.getMetaList()/*, this.getAllEventValues()*/])
      .subscribe(r => {
        this.startUpdateInterval();
      });
  }

  setTimestamp(timestamp: number) {
    this.timestamp = timestamp;
  }

  getNgbTimeStamp() {
    let date = new Date(this.timestamp);
    this.currentDate = {
      year: date.getFullYear(),
      month: date.getMonth() + 1,
      day: date.getDate()
    };
    this.currentTime = {
      hour: date.getHours(),
      minute: date.getMinutes(),
      second: date.getSeconds()
    };
    console.log(this.currentDate);
    console.log(this.currentTime);
  }

  getCurrentDate(): number {
    return Date.now();
  }

  getData() {
    if (!this.isListMode)
      this.getSnapshot();
    else
      this.getList();
  }

  getMetaListOfDevice() {
    this.metaListOfDevice = this._metaList.filter((m) => { return m.device === this._device; });
  }

  startUpdateInterval() {
    this._stopped = false;
    this._updateInterval = setInterval(() => {
      this.getData();
      this.setTimestamp(this.timestamp + this._updateIntervalTimeCurrent);
    }, 1000);
  }

  stopUpdateInterval() {
    this._stopped = true;
    if (this._updateInterval) {
      clearInterval(this._updateInterval);
      this._updateInterval = undefined;
    }
  }

  updateIntervalTime(updateTime: number) {
    this.stopUpdateInterval();
    this._updateIntervalTimeCurrent = updateTime;
    this.startUpdateInterval();
  }

  getSnapshot() {
    if (this._activeSnapshotRequest)
      this._activeSnapshotRequest.unsubscribe();

    this._activeSnapshotRequest = this.apiService.getSnapShot(this.isAutoMode ? "auto" : this.device, new Date(this.timestamp))
      .subscribe(r => {
        if (!this.isAutoMode && this.device)
          this.snapshot = r[this.device];
        else {
          for (let d in r)
            if (r[d]) {
              this.device = d as DeviceType;
              this.snapshot = r[d];
              break;
            }
        }
        this.events$.next(this.snapshot?.event_log ?? []);
        this.noData = !this.snapshot || !this.snapshot.status;
        if (this.noData) {
          if (!this.isAutoMode)
            this.isAutoMode = true;
          else
            this._device = null;
        }
        this.isDataLoaded = true;
      });
  }

  getList(timestamp?: Date, sequence?: number) {
    if (this._activeListRequest)
      this._activeListRequest.unsubscribe();

    this._activeListRequest = this.apiService.getList(this.device, timestamp ?? new Date(this.timestamp), this.listWindow, sequence)
      .subscribe(r => {
        this.processList(r ?? []);
        this.list$.next(r);
        this._lastListTimestamp = this.timestamp;
      });
  }

  processList(list: ListItem[]) {
    for (let item of list) {
      let meta = this.getMeta(item);
      item.category = (meta.category ?? "?");
      item.unit = meta.unit;
      item.name = meta.nice_name ?? meta.name ?? meta.data_id;
    }
  }

  getMetaList(): Observable<Meta[]> {
    return this.apiService.getMeta()
      .pipe(
        tap(r => {
        this._metaList = r ?? [];
        this.getMetaListOfDevice();
      }));
  }

  getAllEventValues(): Observable<EventValues[]> {
    return this.apiService.getEventValues(this.device)
      .pipe(
        tap(r => {
        this._allEventValues = r ?? [];
      }));
  }

  back() {
    this.setTimestamp(this.timestamp - this.backwardTime * 1000);
    if (this._stopped)
      this.getData();
  }

  selectNavButton(node: HTMLElement) {
    node = node.closest('span');
    let nodes = node.parentElement.querySelectorAll("span");
    for (let i = 0; i < nodes.length; i++)
      nodes.item(i).classList.remove("selected");
    node.classList.add("selected");
  }

  play($event: Event) {
    this.updateIntervalTime(this._updateIntervalTimeNormal);
    this.selectNavButton($event.target as HTMLElement);
  }

  pause($event: Event) {
    this.stopUpdateInterval();
    this.selectNavButton($event.target as HTMLElement);
  }

  fastForward($event: Event) {
    this.updateIntervalTime(this._updateIntervalTimeFast);
    this.selectNavButton($event.target as HTMLElement);
  }

  forward() {
    this.setTimestamp(this.timestamp + this.forwardTime * 1000);
    if (this._stopped)
      this.getData();
  }

  now() {
    this.setTimestamp(this.getCurrentDate());
    if (this._stopped)
      this.getData();
  }

  getMeta(item: ListItem): Meta {
    return this._metaList.find((value: Meta, index: number, obj: Meta[]) => {
      return value.device === this.device && value.data_id === item.data_id;
    });
  }

  getListItemInfo(item: ListItem): string {
    if (!item)
      return "";

    let category = this.getListItemCategory(item);
    let unit = (item.unit ?? "").toLowerCase().replace("/", "-");
    return category + " " + unit;
  }

  getListItemCategory(item: ListItem): string {
    if (!item)
      return "";

    if (item.category === Category.Event)
      return "event";

    if (item.category === Category.Sample)
      return "sample";

    if (item.category === Category.Condition) {
      if ((item.value ?? "").toLowerCase().indexOf("normal") > -1)
        return "c-normal";
      if ((item.value ?? "").toLowerCase().indexOf("warning") > -1)
        return "c-warning";
      if ((item.value ?? "").toLowerCase().indexOf("fault") > -1)
        return "c-fault";
      if ((item.value ?? "").toLowerCase().indexOf("unavailable") > -1)
        return "c-unavaliable";
    }

    return "";
  }

  openSearch() {
    this.searchDialog.show();
  }

  search(model: MetricFilterModel) {
    console.log(model);

    let req: FindParams = {
      device: this.device,
      afterCount: model.direction === "1" ? 1 : undefined,
      beforeCount: model.direction === "-1" ? 1 : undefined,
      category: model.metricType,
      relation: model.relation,
      value: (model.value ?? "").toString().split('|'),
      name: model.metricId,
      extra: model.extra,
      timestamp: new Date(this.timestamp)
    };

    if (!req.afterCount && !req.beforeCount) {
      req.beforeCount = 1;
    }

    this.apiService.find(req).subscribe(r => {
      console.log(r);
      let t = this.timestamp;
      if ((r ?? []).length > 0)
        t = new Date(r[0].timestamp).getTime();
      this.setTimestamp(t);
      this.searchDialog.close();
    }, (err: HttpErrorResponse) => {
      let message = "";
      if (err.status === 404)
        message = err?.error?.detail ?? "No log found!";
      else
        message = err?.error?.detail ?? "Some error happened!";
      this.searchDialog.showError(message);
    });
  }

  dateTimeSettingsShown() {
    this.getNgbTimeStamp();
  }

  setDate(d: NgbDateStruct) {
    let date = new Date(this.timestamp);
    date.setFullYear(d.year, d.month - 1, d.day);
    this.setTimestamp(date.getTime());
    if (this._stopped)
      this.getData();
  }

  setTime(t: NgbTimeStruct) {
    let date = new Date(this.timestamp);
    date.setHours(t.hour, t.minute, t.second);
    this.setTimestamp(date.getTime());
    if (this._stopped)
      this.getData();
  }

  changeLayout(layout: string) {
    this.isListMode = layout === "list";
    if (layout === "list" && this._stopped && this._lastListTimestamp != this.timestamp) {
      this.getList();
    }
  }

  stepList(item: ListItem, direction: number) {
    this.timestamp =  new Date(item.timestamp).getTime();
    this.getList(new Date(item.timestamp), item.sequence);
  }

  ngOnDestroy() {
    this.stopUpdateInterval();
  }

  changeDevice(device: DeviceType) {
    this.device = device;
    this.isAutoMode = false;
  }

  autoModeChange() {
    this.isAutoMode = !this.isAutoMode;
    if (!this.isAutoMode && !this.device)
      this.device = DeviceType.Mill;
  }
}
