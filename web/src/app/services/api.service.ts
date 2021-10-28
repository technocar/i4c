import { HttpClient, HttpHeaders, HttpParams } from '@angular/common/http';
import { Inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from 'src/environments/environment';
import { ErrorDetail, EventValues, FindRequest, FindResponse, ListItem, Meta, Project, ProjectInstallResponse, ProjectStatus, SnapshotResponse, User } from './models/api';
import { DeviceType } from './models/constants';

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
    if (!error || !error.detail)
      return "Ismeretlen hiba!";

    if (Array.isArray(error.detail)) {
      let details: ErrorDetail[] = error.detail;
      if (details.length === 0)
        return "Ismeretlen hiba!";

      return details.map((d) => d.msg);
    }

    return (error.detail as ErrorDetail).msg;
  };

  login(): Observable<User> {
    return this.http.get<User>(`${this._apiUrl}/login`);
  }

  getSnapShot(device: string, timestamp: Date): Observable<SnapshotResponse> {
    return this.http.get<SnapshotResponse>(`${this._apiUrl}/log/snapshot`, { params: { ts: timestamp.toISOString(), device: device } });
  }

  getList(device: DeviceType, timestamp: Date, window: number, sequence?: number): Observable<ListItem[]> {
    let request: FindRequest = {
      device: device,
      timestamp: timestamp,
      afterCount: window,
      beforeCount: window,
      sequence: sequence
    };
    return this.find(request);
  }

  find(request: FindRequest): Observable<ListItem[]> {
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
    var params = new HttpParams()
      .append("name", name)
      .append("status", status)
      .append("file", file);

    params.keys().forEach((p) => {
      if (params.get(p) === undefined)
        params = params.delete(p);
    });

    return this.http.get<Project[]>(`${this._apiUrl}/projects`, { params });
  }

  installProject(name: string, version: string, statuses?: ProjectStatus[]): Observable<ProjectInstallResponse> {
    var params = new HttpParams()
      .append("statuses", JSON.stringify(statuses));
    return this.http.post<ProjectInstallResponse>(`${this._apiUrl}/installations/${name}/${version}`, undefined, { params });
  }
}
