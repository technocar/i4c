import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';

import { ToolsRoutingModule } from './tools-routing.module';
import { ToolsComponent } from './tools.component';
import { CommonsModule } from '../commons/commons.module';
import { FormsModule } from '@angular/forms';
import { NgbDatepickerModule, NgbModalModule, NgbTimepickerModule } from '@ng-bootstrap/ng-bootstrap';
import { ToolDetailsComponent } from './tool-details/tool-details.component';


@NgModule({
  declarations: [
    ToolsComponent,
    ToolDetailsComponent
  ],
  imports: [
    CommonModule,
    ToolsRoutingModule,
    CommonsModule,
    FormsModule,
    NgbDatepickerModule,
    NgbTimepickerModule,
    NgbModalModule
  ]
})
export class ToolsModule { }
