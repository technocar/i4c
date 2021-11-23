import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';

import { DashboardRoutingModule } from './dashboard-routing.module';
import { DashboardComponent } from './dashboard.component';
import { SnapshotBaseComponent } from './snapshots/snapshot-base/snapshot-base.component';
import { SnapshotMillComponent } from './/snapshots/snapshot-mill/snapshot-mill.component';
import { SnapshotLatheComponent } from './snapshots/snapshot-lathe/snapshot-lathe.component';
import { SnapshotRobotComponent } from './snapshots/snapshot-robot/snapshot-robot.component';
import { SnapshotGomComponent } from './snapshots/snapshot-gom/snapshot-gom.component';
import { NgbAlertModule, NgbDatepickerModule, NgbDropdownModule, NgbNavModule, NgbPopoverModule, NgbTimepickerModule, NgbTypeaheadModule } from '@ng-bootstrap/ng-bootstrap';
import { FormsModule } from '@angular/forms';
import { CommonsModule }  from '../commons/commons.module';


@NgModule({
  declarations: [
    DashboardComponent,
    SnapshotBaseComponent,
    SnapshotMillComponent,
    SnapshotLatheComponent,
    SnapshotRobotComponent,
    SnapshotGomComponent
  ],
  imports: [
    CommonModule,
    FormsModule,
    DashboardRoutingModule,
    NgbPopoverModule,
    NgbDatepickerModule,
    NgbTimepickerModule,
    NgbNavModule,
    NgbTypeaheadModule,
    NgbAlertModule,
    NgbDropdownModule,
    CommonsModule
  ]
})
export class DashboardModule { }
