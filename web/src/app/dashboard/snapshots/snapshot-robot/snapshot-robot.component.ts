import { Component, OnInit } from '@angular/core';
import { SnapshotBaseComponent } from '../snapshot-base/snapshot-base.component';

@Component({
  selector: 'app-snapshot-robot',
  templateUrl: './snapshot-robot.component.html',
  styleUrls: ['./snapshot-robot.component.scss']
})
export class SnapshotRobotComponent extends SnapshotBaseComponent implements OnInit {

  constructor() {
    super();
  }

  ngOnInit(): void {
  }

}
