import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';

import { CommonsModule } from '../commons/commons.module';
import { FormsModule } from '@angular/forms';
import { ProjectRoutingModule } from './project-routing.module';
import { ProjectComponent } from './project.component';
import { NgbDatepickerModule } from '@ng-bootstrap/ng-bootstrap';


@NgModule({
  declarations: [
    ProjectComponent
  ],
  imports: [
    CommonsModule,
    CommonModule,
    ProjectRoutingModule,
    FormsModule,
    NgbDatepickerModule
  ]
})
export class ProjectModule { }
