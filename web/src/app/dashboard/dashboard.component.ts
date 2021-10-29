import { HttpErrorResponse } from '@angular/common/http';
import { Component, OnInit, ViewChild } from '@angular/core';
import { NgForm } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';
import { NgbActiveModal, NgbDateStruct, NgbModal, NgbTimeStruct, NgbTypeahead } from '@ng-bootstrap/ng-bootstrap';
import { BehaviorSubject, forkJoin, merge, Observable, OperatorFunction, Subject, Subscription } from 'rxjs';
import { debounceTime, distinctUntilChanged, map, tap } from 'rxjs/operators';
import { ApiService } from '../services/api.service';
import { Category, EventLog, EventValues, FindRequest, ListItem, Meta, Snapshot } from '../services/models/api';
import { DeviceType } from '../services/models/constants';

interface Metric {
  id: string,
  name: string,
  type: string,
  level: string,
  children: Metric[]
}

interface SearchError {
  show: boolean,
  message: string
}

interface SearchModel {
  direction: string,
  relation: string,
  metricId: string,
  metricType: string,
  metricName: string,
  value: string,
  extra: string
}

interface SelectedEventValues {
  name: string
}

@Component({
  selector: 'app-dashboard',
  templateUrl: './dashboard.component.html',
  styleUrls: ['./dashboard.component.scss']
})
export class DashboardComponent implements OnInit {
  @ViewChild('eventValuesSelector', {static: true}) instance: NgbTypeahead;
  focus$ = new Subject<string>();
  click$ = new Subject<string>();


  _currentDate: NgbDateStruct;
  _currentTime: NgbTimeStruct;

  _lastListTimestamp: number = 0;
  _stopped: boolean;

  isDataLoaded: boolean = false;
  isEventDataLoaded: boolean = false;
  isListMode: boolean = false;
  listWindow: number = 20;
  metricTree: Metric[] = [];
  searchModel: SearchModel = {
      direction: "-1",
      metricId: undefined,
      metricType: undefined,
      metricName: undefined,
      relation: undefined,
      value: undefined,
      extra: undefined
  };
  searchError: SearchError = {
    show: false,
    message: ""
  };
  selectedEventValues: string[] = [];
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

  isAutoMode: boolean = false;
  snapshot: Snapshot;
  device: DeviceType;
  timestamp: number;
  backwardTime: number = 30; //in seconds
  forwardTime: number = 30; //in seconds

  events$: BehaviorSubject<EventLog[]> = new BehaviorSubject([]);
  list$: BehaviorSubject<ListItem[]> = new BehaviorSubject([]);

  constructor(
    private apiService: ApiService,
    private modalService: NgbModal,
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
        this.metricTree = this.getMetrics(undefined, undefined);
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
        if (!this.isAutoMode)
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
    return this.apiService.getMeta(this.device)
      .pipe(
        tap(r => {
        this._metaList = r ?? [];
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
  }

  now() {
    this.setTimestamp(this.getCurrentDate());
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

  openSearch(content) {
    this.modalService.open(content);
  }

  getMetrics(ids: string[], parentLevels: string[]): Metric[] {
    let children: Metric[] = [];
    let items: Meta[] = [];
    let level: string;
    ids = ids ?? [];
    parentLevels = parentLevels ?? [];
    let parentLevel = parentLevels.length > 0 ? parentLevels[parentLevels.length - 1] : "";
    switch(parentLevel) {
      case "category":
        level = "system1";
        break;
      case "system1":
        level = "system2";
        break;
      case "system2":
        level = "data_id";
        break;
      case "data_id":
        return [];
      default:
        level = "category";
        break;
    }
    items = this._metaList.filter((value: Meta, index: Number, array: Meta[]) => {
      let ok = value.device === this.device;
      if (!ok)
        return false;

      if (ids.length === 0)
        return true;

      for (let i = 0; i < ids.length; i++)
        if (ids[i] !== value[parentLevels[i]])
          return false;

      return true;
    });

    for (let item of items) {
      let idx = children.findIndex((value) => {
        return value.id === item[level]
      });

      if (idx > -1)
        continue;

      let name = level === "data_id" ? item.nice_name : item[level];
      if (name == undefined || name == "")
        name = item.data_id;

      children.push({
        id: item[level],
        name: name,
        type: ids.length === 0 ? item[level] : ids[0],
        level: level,
        children: this.getMetrics(ids.concat([item[level]]), parentLevels.concat([level]))
      });
    }

    children = children.sort((a, b) => {
      return a.name < b.name ? -1 : a.name > b.name ? 1 : 0;
    });

    return children;
  }

  toggleMetricNode(event: Event) {
    let target = (event.target as HTMLElement);
    let isCategorySelection = target.classList.contains("category");
    let allowedNodes = ["LI", "I", "SPAN"];
    if (allowedNodes.indexOf(target.nodeName) === -1 && !isCategorySelection)
      return;

    let node = target.closest('li');

    if (node.classList.contains("leaf") || isCategorySelection) {
      if (this.searchModel.metricType !== node.getAttribute("type")) {
        this.searchModel.value = undefined;
        this.searchModel.relation = undefined;
        this.searchModel.extra = undefined;
      }
      this.searchModel.metricType = node.getAttribute("type");
      if (isCategorySelection) {
        this.searchModel.metricId = undefined;
        this.searchModel.metricName = node.querySelector('span').innerText;
      } else {
        this.searchModel.metricId = node.id;
        this.searchModel.metricName = node.innerText;
      }
      if (this.searchModel.metricType === "EVENT") {
        this.getEventValues(this.searchModel.metricId);
      }
      node.closest(".dropdown-menu").classList.toggle("show");
      let dropdown = node.closest(".dropdown") as HTMLElement;
      dropdown.classList.toggle("show");
      let button = dropdown.querySelector(".dropdown-toggle") as HTMLButtonElement;
      //button.innerText = node.innerText;
      button.setAttribute("aria-expanded", "false");
    } else {
      if (node.classList.contains("closed"))
      {
        node.classList.remove("closed");
        node.classList.add("opened");
      } else {
        node.classList.remove("opened");
        node.classList.add("closed");
      }
    }
  }

  search(form: NgForm, modal: NgbActiveModal) {
    console.log(this.searchModel);

    let req: FindRequest = {
      device: this.device,
      afterCount: this.searchModel.direction === "1" ? 1 : undefined,
      beforeCount: this.searchModel.direction === "-1" ? 1 : undefined,
      category: this.searchModel.metricType,
      relation: this.searchModel.relation,
      value: (this.searchModel.value ?? "").toString().split('|'),
      name: this.searchModel.metricId,
      extra: this.searchModel.extra
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
      modal.close();
    }, (err: HttpErrorResponse) => {
      this.searchError.show = true;
      if (err.status === 404)
        this.searchError.message = err?.error?.detail ?? "No log found!";
      else
        this.searchError.message = err?.error?.detail ?? "Some error happened!";
    });
  }

  searchDataChanged(event: Event) {
    this.searchError.show = false;
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

  getEventValues(id: string) {
    let event = this._allEventValues.find((event) => {
      return event.data_id === id;
    });

    this.selectedEventValues = event?.values ?? [];
  }

  searchForEventValues: OperatorFunction<string, readonly string[]> = (text$: Observable<string>) => {
    const debouncedText$ = text$.pipe(debounceTime(200), distinctUntilChanged());
    const clicksWithClosedPopup$ = this.click$/*.pipe(filter(() => !this.instance.isPopupOpen()))*/;
    const inputFocus$ = this.focus$;

    return merge(debouncedText$, inputFocus$, clicksWithClosedPopup$).pipe(
      map(term => (term === '' ? this.selectedEventValues
        : this.selectedEventValues.filter(v => v.toLowerCase().indexOf(term.toLowerCase()) > -1)).slice(0, 10))
    );
  }

  stepList(item: ListItem, direction: number) {
    this.timestamp =  new Date(item.timestamp).getTime();
    this.getList(new Date(item.timestamp), item.sequence);
  }

  ngOnDestroy() {
    this.stopUpdateInterval();
  }
}
