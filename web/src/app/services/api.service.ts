import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from 'src/environments/environment';
import { ErrorDetail, EventValues, FindParams, ListItem, Meta, Project, ProjectInstall, ProjectInstallParams, ProjectInstallStatus, ProjectStatus, SnapshotResponse, User, WorkPiece, WorkPieceParams, WorkPieceBatch, WorkPieceUpdate, UpdateResult } from './models/api';
import { DeviceType } from './models/constants';

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

@Injectable({
  providedIn: 'root'
})
export class ApiService {

  private _apiUrl: string;

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

  login(): Observable<User> {
    return this.http.get<User>(`${this._apiUrl}/login`);
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

  getMeta(device: DeviceType): Observable<Meta[]> {
    return this.http.get<Meta[]>(`${this._apiUrl}/log/meta`);
  }

  getEventValues(device: DeviceType): Observable<EventValues[]> {
    return this.http.get<EventValues[]>(`${this._apiUrl}/${device}/event_values`);
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

  updateWorkPiece(id: string, parameters: WorkPieceUpdate): Observable<UpdateResult> {
    return this.http.patch<UpdateResult>(`${this._apiUrl}/workpiece/${id}`, parameters);
  }

  getWorkPieceBatches(parameters?: WorkPieceParams): Observable<WorkPieceBatch[]> {
    var params = new RequestParams();
    params.addFromObject(parameters);

    return this.http.get<WorkPieceBatch[]>(`${this._apiUrl}/batch`, { params: params.getAll() });
  }
}
