import { Component, Input, OnInit } from '@angular/core';
import { BehaviorSubject } from 'rxjs';
import { Axis, Condition, Snapshot } from 'src/app/services/models/api';

@Component({
  selector: 'app-snapshot-base',
  templateUrl: './snapshot-base.component.html',
  styleUrls: ['./snapshot-base.component.scss']
})
export class SnapshotBaseComponent implements OnInit {

  private _snapshot: Snapshot;

  conditions$: BehaviorSubject<Condition[]> = new BehaviorSubject([]);
  axesLin$: BehaviorSubject<Axis[]> = new BehaviorSubject([]);
  axesRot$: BehaviorSubject<Axis[]> = new BehaviorSubject([]);

  @Input("snapshot")
  get snapshot(): Snapshot {
    return this._snapshot;
  }
  set snapshot(value: Snapshot) {
    this._snapshot = value;
    this.axesLin$.next(this.snapshot?.status?.lin_axes ?? []);
    this.axesRot$.next(this.snapshot?.status?.rot_axes ?? []);
    this.conditions$.next(this.snapshot?.conditions ?? []);
  }

  constructor() { }

  ngOnInit(): void {
  }

  getAxisMode(axis: Axis): string {
    if (!axis || (axis.mode ?? "") === "")
      return "?";

    if (axis.mode.length > 1)
      return axis.mode[0];
    else
      return axis.mode;
  }

}
