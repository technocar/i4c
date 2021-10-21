import { Component, OnInit } from '@angular/core';
import { SnapshotBaseComponent } from '../snapshot-base/snapshot-base.component';

@Component({
  selector: 'app-snapshot-lathe',
  templateUrl: './snapshot-lathe.component.html',
  styleUrls: ['./snapshot-lathe.component.scss']
})
export class SnapshotLatheComponent extends SnapshotBaseComponent implements OnInit {

  constructor() {
    super();
  }

  ngOnInit(): void {
  }

}
