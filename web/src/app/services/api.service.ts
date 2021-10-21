import { HttpClient, HttpParams } from '@angular/common/http';
import { Inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from 'src/environments/environment';
import { EventValues, FindRequest, FindResponse, ListItem, Meta, SnapshotResponse } from './models/api';
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

  getSnapShot(device: string, timestamp: Date): Observable<SnapshotResponse> {
    return this.http.get<SnapshotResponse>(`${this._apiUrl}/log/snapshot`, { params: { ts: timestamp.toISOString(), device: device } });
  }

  getList(device: DeviceType, timestamp: Date, window: number): Observable<ListItem[]> {
    return this.http.get<ListItem[]>(`${this._apiUrl}/${device}/list`, { params: { ts: timestamp.toISOString(), window: window.toString() } });
  }

  find(request: FindRequest): Observable<FindResponse> {
    var params = new HttpParams();
    params = params.append("device", request.device);
    if (request.before)
      params = params.append("before", request.before.toISOString());
    if (request.after)
      params = params.append("after", request.after.toISOString());
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

    return this.http.get<FindResponse>(`${this._apiUrl}/log/find`, { params });
  }

  getMeta(device: DeviceType): Observable<Meta[]> {
    return this.http.get<Meta[]>(`${this._apiUrl}/log/meta`);
  }

  getEventValues(device: DeviceType): Observable<EventValues[]> {
    return this.http.get<EventValues[]>(`${this._apiUrl}/${device}/event_values`);
  }
}
