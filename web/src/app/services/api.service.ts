import { HttpClient, HttpEvent, HttpEventType, HttpHeaders, HttpParams, HttpResponse } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable, of } from 'rxjs';
import { distinctUntilChanged, map } from 'rxjs/operators';
import { environment } from 'src/environments/environment';
import { ErrorDetail, EventValues, FindParams, ListItem, Meta, Project, ProjectInstall, ProjectInstallParams, ProjectStatus, SnapshotResponse, User, WorkPiece, WorkPieceParams, WorkPieceBatch, WorkPieceUpdate, UpdateResult, ToolListParams, Tool, Device, ToolUsage, StatDef, StatDefParams, StatDefUpdate, StatData, StatXYMetaObjectParam, StatXYMeta } from './models/api';
import { DeviceType } from './models/constants';

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
          v = (value as Date).toISOString();
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
  state: DownloadState
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
    private http: HttpClient
  ) {
    this._apiUrl = environment.apiPath;
  }

  getErrorMsg(error: any): string | string[] {
    console.log(console.error);

    error = error.error ?? error;

    if (!error || !error.detail)
      return "Ismeretlen hiba!";

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

  login(username: string, password: string): Observable<LoginResponse> {
    return this.http.get<LoginResponse>(`${this._apiUrl}/login`, {
      headers: {
        "Authorization": `Basic ${window.btoa(username + ':' + password)}`
      }
    });
  }

  getDevices(): Observable<Device[]> {
    return of([
      { id: DeviceType.Lathe, name: $localize `:@@device_lathe_name:Eszterga` },
      { id: DeviceType.Mill, name: $localize `:@@device_mill_name:Maró` },
      { id: DeviceType.Robot, name: $localize `:@@device_robot_name:Robot` },
      { id: DeviceType.GOM, name: $localize `:@@device_gom_name:GOM` }
    ]);
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
    if (request.name)
      params = params.append("name", request.name);
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
    return this.http.get<Meta[]>(`${this._apiUrl}/log/meta`);
  }

  getEventValues(device: DeviceType): Observable<EventValues[]> {
    return this.http.get<EventValues[]>(`${this._apiUrl}/${device}/event_values`);
  }

  getEventOperations(): string[][] {
    return [
      ['*', $localize `:@@event_operation_*:tartalmaz`],
      ['*!=', $localize `:@@event_operation_*!=:nem tartalmaz`],
      ['=', $localize `:@@event_operation_=:teljes egyezés`],
      ['!=', $localize `:@@event_operation_!=:nem egyezik`]
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
    return this.http.get(`${this._apiUrl}/intfiles/v/${version}/${filename}`, { observe: 'events', reportProgress: true, responseType: 'blob' as 'json' })
      .pipe(
        map((event: HttpEvent<Blob>) => {
          var download: Download = { progress: 0, content: null, state: DownloadState.Pending };
          if (event.type === HttpEventType.DownloadProgress) {
            download.progress = event.loaded / event.total * 100.00;
            download.state = DownloadState.InProgress;
          } else if (event.type === HttpEventType.Response) {
            let response = event as HttpResponse<Blob>;
            download.content = response.body;
            download.contentType = response.body.type;
            download.filename = this.getFileName(response);
            download.state = DownloadState.Done;
            this.saveAs(download);
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
    if (id == "-1")
      return of({
        id: -1,
        modified: (new Date()).toISOString(),
        name: "új elemzés",
        shared: false,
        timeseriesdef: undefined,
        xydef: undefined,
        user: undefined
      });
    else
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

  getStatXYMeta(after: Date): Observable<StatXYMeta> {
    var params = new RequestParams();
    params.add("after", after);
    return this.http.get<StatXYMeta>(`${this._apiUrl}/stat/xymeta`, { params: params.getAll() });
  }

  getAnalysisData(id: string): Observable<[StatDef, Meta[]]> {
    return new Observable<[StatDef, Meta[]]>((observer) => {
      var result: [StatDef, Meta[]] = [undefined, undefined];
      this.getStatDef(id).subscribe(def => {
        result[0] = def;
        if (!def) {
          observer.next(result);
          observer.complete();
        } else {
          if (def.timeseriesdef)
            this.getMeta().subscribe(meta => {
              result[1] = meta;
              observer.next(result);
              observer.complete();
            },
            (err) => { observer.error(err); observer.complete(); });
          else {
            observer.next(result);
            observer.complete();
          }
        }
      },
      (err) => { observer.error(err); observer.complete(); });

      return {
        unsubscribe() {
        }
      };
    });
  }
}
