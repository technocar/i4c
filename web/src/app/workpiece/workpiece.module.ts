import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';

import { WorkPieceRoutingModule } from './workpiece-routing.module';
import { WorkPieceComponent } from './list/workpiece.component';
import { CommonsModule } from '../commons/commons.module';
import { FormsModule } from '@angular/forms';
import { NgbAccordionModule, NgbDatepickerModule, NgbPopoverModule } from '@ng-bootstrap/ng-bootstrap';
import { WorkpieceDetailComponent } from './workpiece-detail/workpiece-detail.component';


@NgModule({
  declarations: [
    WorkPieceComponent,
    WorkpieceDetailComponent
  ],
  imports: [
    CommonsModule,
    CommonModule,
    WorkPieceRoutingModule,
    FormsModule,
    NgbDatepickerModule,
    NgbPopoverModule,
    NgbAccordionModule
  ]
})
export class WorkpieceModule { }
