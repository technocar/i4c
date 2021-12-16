import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';

import { AlarmRoutingModule } from './alarm-routing.module';
import { AlarmComponent } from './alarm.component';
import { CommonsModule } from '../commons/commons.module';
import { FormsModule } from '@angular/forms';
import { AlarmDetailComponent } from './detail/detail.component';


@NgModule({
  declarations: [
    AlarmComponent,
    AlarmDetailComponent
  ],
  imports: [
    CommonModule,
    AlarmRoutingModule,
    CommonsModule,
    FormsModule
  ]
})
export class AlarmModule { }
