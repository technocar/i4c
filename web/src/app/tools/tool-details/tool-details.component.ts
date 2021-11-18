import { Component, Input, OnInit, ViewChild } from '@angular/core';
import { NgForm } from '@angular/forms';
import { BehaviorSubject, forkJoin, Observable, of } from 'rxjs';
import { ApiService } from 'src/app/services/api.service';
import { Device, Tool, ToolUsage } from 'src/app/services/models/api';
import { DeviceType } from 'src/app/services/models/constants';
import { __createBinding } from 'tslib';

@Component({
  selector: 'app-tool-details',
  templateUrl: './tool-details.component.html',
  styleUrls: ['./tool-details.component.scss']
})
export class ToolDetailsComponent implements OnInit {

  @Input("tool")
  set origTool(value: Tool) {
    this._origTool = value;
  }
  @ViewChild("form") form: NgForm;

  private _currTool: Tool;
  private _origTool: Tool;

  loaded: boolean = false;
  hasChanges: boolean = false;
  isTimestampChanged: boolean = false;
  isNew: boolean = false;
  submitted: boolean = false;
  get tool(): Tool { return this._currTool; }
  set tool(value: Tool) { this._currTool = value; }
  devices$: BehaviorSubject<Device[]> = new BehaviorSubject([]);
  events: string[][] = [];
  toolUsages$: BehaviorSubject<ToolUsage[]> = new BehaviorSubject([]);

  constructor(
    private apiService: ApiService)
  { }

  ngOnInit(): void {
    this.events = this.apiService.getToolEventTypes();
    var d$ = this.apiService.getDevices();
    var tu$ = this.apiService.getToolUsageList();
    forkJoin([d$, tu$]).subscribe(r => {
      this.devices$.next(r[0]);
      this.toolUsages$.next(r[1]);
      this.init();
    });
  }

  init() {
    this.isNew = false;
    this.hasChanges = false;
    this.isTimestampChanged = false;
    this.loaded = false;
    try {
      if (this._origTool === undefined) {
        this.isNew = true;
        this.createEmptyTool();
        this.hasChanges = true;
      } else {
        this._currTool = Object.assign({}, this._origTool);
      }
    } catch(e) {
      console.error(e);
    }
    this.loaded = true;
  }

  createEmptyTool() {
    this._origTool = {
      device: this.devices$.value[0].id,
      timestamp: (new Date()).toISOString(),
      sequence: 1
    };
    this._currTool = Object.assign({}, this._origTool);
  }

  detectToolChanges() {
    var a: Tool = this._origTool ?? {};
    var b: Tool = this._currTool ?? {};
    for (let p in a) {
      if (a[p] !== b[p]) {
        this.hasChanges = true;
        break;
      }
    }
    this.isTimestampChanged = a.timestamp !== b.timestamp;
  }

  onChange(item: string, value: any) {
    switch(item) {
      case "timestamp":
        this._currTool.timestamp = value ? new Date(value).toISOString() : undefined;
        break;
      default:
        this._currTool[item] = value;
        break;
    }
    this.detectToolChanges();
  }

  save(): Observable<boolean> {
    this.submitted = true;
    var result = new Observable<boolean>((observer) => {
    if (this.form.invalid)
      observer.next(false);
    else if (this.isNew || (this.hasChanges && !this.isTimestampChanged))
      this.apiService.updateTool(this._currTool)
      .subscribe(r => {
        observer.next(true);
      }, (err) => {
        observer.next(false);
      });
    else if (this.hasChanges && this.isTimestampChanged) {
      this.apiService.deleteTool(this._origTool)
        .subscribe(() => {
          this.apiService.updateTool(this._currTool)
            .subscribe(r => {
              observer.next(true);
            },
            (err) => {
              observer.next(false);
            });
        }, (err) => {
          observer.next(false);
        });
    }
    });
    return result;
  }
}
