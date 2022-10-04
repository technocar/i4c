import { HttpClient, HttpEvent, HttpEventType, HttpHeaders, HttpParams, HttpResponse } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { BehaviorSubject, forkJoin, Observable, of, throwError } from 'rxjs';
import { catchError, distinctUntilChanged, filter, map, takeUntil, takeWhile } from 'rxjs/operators';
import { environment } from 'src/environments/environment';
import { AuthenticationService } from './auth.service';
import { ErrorDetail, EventValues, FindParams, ListItem, Meta, Project, ProjectInstall, ProjectInstallParams, ProjectStatus, SnapshotResponse, User, WorkPiece, WorkPieceParams, WorkPieceBatch, WorkPieceUpdate, UpdateResult, ToolListParams, Tool, Device, ToolUsage, StatDef, StatDefParams, StatDefUpdate, StatData, StatXYMetaObjectParam, StatXYMeta, Alarm, AlarmRequestParams, AlarmSubscription, AlarmSubscriptionRequestParams, AlarmSubscriptionGroupGrant, AlarmSubscriptionUpdate, AlarmGroup, StringRelation } from './models/api';
import { DeviceType } from './models/constants';
import { AnalysisService } from '../analyses/analysis/analysis.service';

export interface LoginResponse {
  user: User
}
class RequestParams {
  _params: HttpParams;

  constructor() {
    this._params = new HttpParams();
  }

  public add(name: string, value: any) {
    console.log(value);
    if (value === undefined)
      return;

    let v: string = "";
    switch (typeof value) {
      case "object":
        if (value instanceof Date)
          try {
            v = (value as Date).toISOString();
          } catch {
            v = undefined;
          }
        else if (Array.isArray(value))
        {
          for (let item of v)
            this.add(name, item);
          return;
        }
        else
          v = JSON.stringify(value);
        break;
      default:
        v = value.toString();
        break;
    }
    console.log(v);

    if (v === undefined)
      return;

    if (name.endsWith("_mask")) {
      for (let filter of v.split(' '))
        this._params = this._params.append(name, filter);
    } else
      this._params = this._params.append(name, v);
  }

  public addFromObject(object: Object) {
    if (!object)
      return;

    for (let name in object)
      this.add(name, object[name]);
  }

  public getAll(): HttpParams {
    return this._params;
  }
}

export enum DownloadState { Pending = 0, InProgress = 1, Done = 2 }

export interface Download {
  content: Blob,
  contentType?: string;
  filename?: string;
  progress: number,
  state: DownloadState,
  statusCode: number,
  error?: any
}

@Injectable({
  providedIn: 'root'
})
export class ApiService {

  private _apiUrl: string;

  private _toolEventTypes: string[][] = [
    ["install_tool", $localize `:@@tools_event_install_tool:Beszerelés`],
    ["remove_tool", $localize `:@@tools_event_remove_tool:Kiszerelés`]
  ];

  private _workpieceStatuses: string[][] = [
    ['', ' - '],
    ['good', $localize `:@@workpiece_status_good:Megfelel`],
    ['bad', $localize `:@@workpiece_status_bad:Selejt`],
    ['inprogress', $localize `:@@workpiece_status_inprogress:Folyamatban`],
    ['unknown', $localize `:@@workpiece_status_unknown:Ismeretlen`]
  ];

  constructor(
    private http: HttpClient,
    private auth: AuthenticationService,
    private analysis: AnalysisService
  ) {
    this._apiUrl = environment.apiPath;
    console.log(this._apiUrl);
  }

  getErrorMsg(error: any): string | string[] {
    console.log(error);

    error = error?.error?.status ?? error;

    if (!error)
      return "Ismeretlen hiba!";

    if (!error.detail)
      return typeof error === "string" ? error : (error.message ?? error.statusText)

    if (Array.isArray(error.detail)) {
      let details: ErrorDetail[] = error.detail;
      if (details.length === 0)
        return "Ismeretlen hiba!";

      return details.map((d) => d.msg);
    }

    if (typeof error.detail !== "object")
      return error.detail.toString();

    return (error.detail as ErrorDetail).msg;
  };

  login(username: string, password: string): Observable<User> {
    return this.http.get<User>(`${this._apiUrl}/login`, {
      headers: {
        "Authorization": `Basic ${window.btoa(username + ':' + password)}`
      }
    });
  }

  requestNewPassword(username: string): Observable<string> {
    return this.http.post<string>(`${this._apiUrl}/pwdreset/init`, { loginname: username });
  }

  setNewPassword(username: string, token: string, password: string): Observable<User> {
    return this.http.post<User>(`${this._apiUrl}/pwdreset/setpass`, { loginname: username, token: token, password: password });
  }

  getDevices(withEmpty: boolean = true): Observable<Device[]> {
    let devices = [
      { id: DeviceType.Lathe, name: $localize `:@@device_lathe_name:Eszterga` },
      { id: DeviceType.Mill, name: $localize `:@@device_mill_name:Maró` },
      { id: DeviceType.Robot, name: $localize `:@@device_robot_name:Robot` },
      { id: DeviceType.GOM, name: $localize `:@@device_gom_name:GOM` },
      { id: DeviceType.Renishaw, name: $localize `:@@device_renishaw_name:Renishaw` }
    ];
    if (withEmpty)
      devices.splice(0, 0, ...[{ id: DeviceType.Empty, name: "-" }])
    return of(devices);
  }

  getSnapShot(device: string, timestamp: Date): Observable<SnapshotResponse> {
    return this.http.get<SnapshotResponse>(`${this._apiUrl}/log/snapshot`, { params: { ts: timestamp.toISOString(), device: device } });
  }

  getList(device: DeviceType, timestamp: Date, window: number, sequence?: number): Observable<ListItem[]> {
    let request: FindParams = {
      device: device,
      timestamp: timestamp,
      afterCount: window,
      beforeCount: window,
      sequence: sequence
    };
    return this.find(request);
  }

  find(request: FindParams): Observable<ListItem[]> {
    var params = new HttpParams();
    params = params.append("device", request.device);
    if (request.beforeCount)
      params = params.append("before_count", request.beforeCount.toString());
    if (request.afterCount)
      params = params.append("after_count", request.afterCount.toString());
    if (request.category)
      params = params.append("categ", request.category);
    if (request.data_id)
      params = params.append("data_id", request.data_id);
    if (request.value) {
      for (let v of request.value as Array<string>)
        params = params.append("val", v);
    }
    if (request.relation)
      params = params.append("rel", request.relation);
    if (request.extra)
      params = params.append("extra", request.extra);
    if (request.sequence)
      params = params.append("sequence", request.sequence.toString());
    if (request.timestamp)
      params = params.append("timestamp", request.timestamp.toISOString());

    return this.http.get<ListItem[]>(`${this._apiUrl}/log/find`, { params });
  }

  getMeta(): Observable<Meta[]> {
    if (this.auth.hasPrivilige('get/log/meta'))
      return this.http.get<Meta[]>(`${this._apiUrl}/log/meta`);
    else
      return of([]);
  }

  getEventValues(device: DeviceType): Observable<EventValues[]> {
    return this.http.get<EventValues[]>(`${this._apiUrl}/${device}/event_values`);
  }

  getEventOperations(): string[][] {
    return [
      [StringRelation.Contains, $localize `:@@event_operation_*=:∈`],
      [StringRelation.NotContains, $localize `:@@event_operation_*!=:∉`],
      [StringRelation.Equal, $localize `:@@event_operation_=:=`],
      [StringRelation.NotEqual, $localize `:@@event_operation_!=:≠`]
    ];
  }

  getProjects(name?: string, status?: string, file?: string): Observable<Project[]> {
    var params = new RequestParams();
    params.add("name", name);
    params.add("status", status);
    params.add("file", file);

    return this.http.get<Project[]>(`${this._apiUrl}/projects`, { params: params.getAll() });
  }

  getInstalledProjects(parameters?: ProjectInstallParams): Observable<ProjectInstall[]> {
    var params = new RequestParams();
    params.addFromObject(parameters);

    return this.http.get<ProjectInstall[]>(`${this._apiUrl}/installations`, { params: params.getAll() });
  }

  installProject(name: string, version: string, statuses?: ProjectStatus[]): Observable<ProjectInstall> {
    var params = new RequestParams();
    params.add("statuses", statuses);
    return this.http.post<ProjectInstall>(`${this._apiUrl}/installations/${name}/${version}`, undefined, { params: params.getAll() });
  }

  getWorkPieces(parameters?: WorkPieceParams): Observable<WorkPiece[]> {
    var params = new RequestParams();
    params.addFromObject(parameters);

    return this.http.get<WorkPiece[]>(`${this._apiUrl}/workpiece`, { params: params.getAll() });
  }

  getWorkPiece(id: string, deleted?: boolean): Observable<WorkPiece> {
    var params = new RequestParams();
    params.add("with_deleted", deleted);
    return this.http.get<WorkPiece>(`${this._apiUrl}/workpiece/${id}`, { params: params.getAll() });
  }

  getWorkPieceStatuses(): string[][] {
    return this._workpieceStatuses;
  }

  updateWorkPiece(id: string, parameters: WorkPieceUpdate): Observable<UpdateResult> {
    return this.http.patch<UpdateResult>(`${this._apiUrl}/workpiece/${id}`, parameters);
  }

  getWorkPieceBatches(parameters?: WorkPieceParams): Observable<WorkPieceBatch[]> {
    var params = new RequestParams();
    params.addFromObject(parameters);

    return this.http.get<WorkPieceBatch[]>(`${this._apiUrl}/batch`, { params: params.getAll() });
  }

  getFile(filename: string, version: number): Observable<Download> {
    var error$ = new BehaviorSubject(false);
    return this.http.get(`${this._apiUrl}/intfiles/v/${version}/${filename}`, { observe: 'events', reportProgress: true, responseType: 'blob' as 'json' })
      .pipe(
        catchError((err, caught) => {
          error$.next(true);
          throw err;
        }),
        takeWhile(() => error$.value !== true),
        filter((event: HttpEvent<Blob>) => {
          switch(event.type) {
            case HttpEventType.DownloadProgress:
            case HttpEventType.Response:
              return true;
            default:
              return false;
          }
        }),
        map((event: HttpEvent<Blob>) => {
          var download: Download = { progress: 0, content: null, state: DownloadState.Pending, statusCode: 0 };
          if (event.type === HttpEventType.DownloadProgress) {
            download.progress = event.loaded / event.total * 100.00;
            download.state = DownloadState.InProgress;
          } else if (event.type === HttpEventType.Response) {
            if (event.status === 200) {
              let response = event as HttpResponse<Blob>;
              download.content = response.body;
              download.contentType = response.body.type;
              download.filename = this.getFileName(response);
              download.state = DownloadState.Done;
              this.saveAs(download);
            } else {
              download.content = event.body;
              download.contentType = event.body.type;
              download.filename = "";
              download.state = DownloadState.Done;
              download.statusCode = event.status;
            }
          }
          return download;
        }),
        distinctUntilChanged((a, b) => a.state === b.state
          && a.progress === b.progress
          && a.content === b.content
        )
      );
  }

  saveAs(download: Download) {
    let binaryData = [];
    binaryData.push(download.content);
    let downloadLink = document.createElement('a');
    downloadLink.href = window.URL.createObjectURL(new Blob(binaryData, {type: download.contentType}));
    if (download.filename)
        downloadLink.setAttribute('download', download.filename);
    document.body.appendChild(downloadLink);
    downloadLink.click();
  }

  getFileName(response: HttpResponse<Blob>) {
    let filename: string;
    try {
      const contentDisposition: string = response.headers.get('content-disposition');
      const r = /(?:filename=")(.+)(?:")/
      filename = r.exec(contentDisposition)[1];
    }
    catch (e) {
      filename = 'myfile.txt'
    }
    return filename
  }

  getTools(parameters: ToolListParams): Observable<Tool[]> {
    var params = new RequestParams();
    params.addFromObject(parameters);
    return this.http.get<Tool[]>(`${this._apiUrl}/tools`, { params: params.getAll() });
  }

  getToolUsageList(): Observable<ToolUsage[]> {
    return this.http.get<ToolUsage[]>(`${this._apiUrl}/tools/list_usage`);
  }

  getToolEventTypes(): string[][] {
    return this._toolEventTypes;
  }

  updateTool(tool: Tool): Observable<string> {
    return this.http.put<string>(`${this._apiUrl}/tools`, tool);
  }

  deleteTool(tool: Tool): Observable<ArrayBuffer> {
    var options = {
      headers: new HttpHeaders({
        'Content-type': 'application/json'
      }),
      body: tool
    };
    return this.http.delete<ArrayBuffer>(`${this._apiUrl}/tools`, options);
  }

  getStatDefs(parameters: StatDefParams): Observable<StatDef[]> {
    var params = new RequestParams();
    params.addFromObject(parameters);
    return this.http.get<StatDef[]>(`${this._apiUrl}/stat/def`, { params: params.getAll() });
  }

  getStatDef(id: string): Observable<StatDef> {
    return this.http.get<StatDef>(`${this._apiUrl}/stat/def/${id}`);
  }

  addNewStatDef(def: StatDef): Observable<StatDef> {
    def.id = undefined;
    return this.http.post<StatDef>(`${this._apiUrl}/stat/def`, def);
  }

  updateStatDef(id: number, updateObj: StatDefUpdate): Observable<UpdateResult> {
    return this.http.patch<UpdateResult>(`${this._apiUrl}/stat/def/${id}`, updateObj);
  }

  getStatData(id: number): Observable<StatData> {
    return this.http.get<StatData>(`${this._apiUrl}/stat/data/${id}`);
  }

  getStatXYMeta(after: Date): Observable<StatXYMeta[]> {
    var params = new RequestParams();
    params.add("after", after);
    return this.http.get<StatXYMeta[]>(`${this._apiUrl}/stat/objmeta`, { params: params.getAll() });
  }

  //This method for resolver of analsysis module to download data for selected analysis
  getAnalysisData(id: string, type: string, caption: string): Observable<[StatDef, Meta[], string[], string]> {
    return new Observable<[StatDef, Meta[], string[], string]>((observer) => {
      var result: [StatDef, Meta[], string[], string] = [undefined, undefined, undefined, undefined];
      var reqs: Observable<any>[] = [];
      reqs.push( this.getCustomers());
      //Get analysis definition...
      if (id === "-1") {
        result[0] = {
          id: -1,
          modified: (new Date()).toISOString(),
          name: caption ?? "új elemzés",
          shared: false,
          customer: undefined,
          timeseriesdef: undefined,
          xydef: undefined,
          listdef: undefined,
          capabilitydef: undefined,
          user: undefined
        };
        if (["0", "3"].indexOf(type) > -1)
          reqs.push(this.getMeta());
        else
          reqs.push(of(undefined));

        forkJoin(reqs).subscribe(results => {
          result[1] = results[1];
          result[2] = results[0];
          observer.next(result);
          observer.complete();
        }, err => {
          observer.error(err); observer.complete();
        });
      } else {
        reqs.push(this.getStatDef(id));
        forkJoin(reqs).subscribe(results => {
          result[2] = results[0];
          var def = results[1];
          result[0] = def;
          result[3] = this.analysis.getAnalysisTypeDesc(this.analysis.getAnalysisType(def));
          if (def?.timeseriesdef || def?.capabilitydef) {
            //If it's timeseries then gets meta list...
            this.getMeta().subscribe(meta => {
              result[1] = meta;
              observer.next(result);
              observer.complete();
            },
            (err) => { observer.error(err); observer.complete(); });
          } else {
            //If it's not timeseries we are done.
            observer.next(result);
            observer.complete();
          }
        }, err => {
          observer.error(err); observer.complete();
        });
      }

      return {
        unsubscribe() {
        }
      };
    });
  }

  getAlarms(parameters: AlarmRequestParams): Observable<Alarm[]> {
    var params = new RequestParams();
    params.addFromObject(parameters);
    return this.http.get<Alarm[]>(`${this._apiUrl}/alarm/defs`, { params: params.getAll() });
  }

  getAlarm(name: string): Observable<Alarm> {
    return this.http.get<Alarm>(`${this._apiUrl}/alarm/defs/${name}`);
  }

  setAlarm(name: string, alarm: Alarm): Observable<Alarm> {
    return this.http.put<Alarm>(`${this._apiUrl}/alarm/defs/${name}`, alarm);
  }

  getAlarmGroups(user?: string, group?: string): Observable<AlarmGroup[]> {
    var params = new RequestParams();
    params.add("user", user);
    params.add("group", group);
    return this.http.get<AlarmGroup[]>(`${this._apiUrl}/alarm/subsgroups`, { params: params.getAll() });
  }

  getAlarmUserGroups(user: string): Observable<AlarmSubscriptionGroupGrant[]> {
    var params = new RequestParams();
    if ((user ?? "") !== "")
      params.add("user", user);
    return this.http.get<AlarmSubscriptionGroupGrant[]>(`${this._apiUrl}/alarm/subsgroupusage`, { params: params.getAll() });
  }

  getAlarmSubscriptions(parameters: AlarmSubscriptionRequestParams): Observable<AlarmSubscription[]> {
    var params = new RequestParams();
    params.addFromObject(parameters);
    return this.http.get<AlarmSubscription[]>(`${this._apiUrl}/alarm/subs`, { params: params.getAll() });
  }

  getAlarmSubscription(id: number): Observable<AlarmSubscription> {
    return this.http.get<AlarmSubscription>(`${this._apiUrl}/alarm/subs/${id}`);
  }

  addAlarmSubscription(subs: AlarmSubscription): Observable<AlarmSubscription> {
    return this.http.post<AlarmSubscription>(`${this._apiUrl}/alarm/subs`, subs);
  }

  updateAlarmSubscription(id: number, update: AlarmSubscriptionUpdate): Observable<UpdateResult> {
    return this.http.patch<UpdateResult>(`${this._apiUrl}/alarm/subs/${id}`, update);
  }

  getSetting(key: string): Observable<string> {
    return this.http.get<string>(`${this._apiUrl}/settings/${key}`);
  }

  getCustomers(): Observable<string[]> {
    if (this.auth.hasPrivilige("get/customers"))
      return this.http.get<string[]>(`${this._apiUrl}/customers`);
    else
      return of([]);
  }

  getUsers(activeOnly: boolean): Observable<User[]> {
    var params = new RequestParams();
    if (this.auth.hasPrivilige("get/users")) {
      params.add("active_only", activeOnly)
      return this.http.get<User[]>(`${this._apiUrl}/users`, { params: params.getAll() });
    } else if (this.auth.hasPrivilige("get/users/{id}")) {
      return this.http.get<User>(`${this._apiUrl}/users/${this.auth.currentUserValue.id}`).pipe(map(u => [u]));
    } else
      return of([]);
  }
}
