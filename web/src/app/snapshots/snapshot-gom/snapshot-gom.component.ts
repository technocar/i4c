import { Component, OnInit } from '@angular/core';
import { SnapshotBaseComponent } from '../snapshot-base/snapshot-base.component';

@Component({
  selector: 'app-snapshot-gom',
  templateUrl: './snapshot-gom.component.html',
  styleUrls: ['./snapshot-gom.component.scss']
})
export class SnapshotGomComponent extends SnapshotBaseComponent implements OnInit {

  constructor() {
    super();
  }

  ngOnInit(): void {
  }

}
