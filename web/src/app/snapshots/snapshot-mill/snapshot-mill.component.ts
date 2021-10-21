import { Component, Input, OnInit } from '@angular/core';
import { Snapshot } from 'src/app/services/models/api';
import { SnapshotBaseComponent } from '../snapshot-base/snapshot-base.component';

@Component({
  selector: 'app-snapshot-mill',
  templateUrl: './snapshot-mill.component.html',
  styleUrls: ['./snapshot-mill.component.scss']
})
export class SnapshotMillComponent extends SnapshotBaseComponent implements OnInit {

  constructor() {
    super();
  }

  ngOnInit(): void {
  }

}
