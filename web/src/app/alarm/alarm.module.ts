import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';

import { AlarmRoutingModule } from './alarm-routing.module';
import { AlarmComponent } from './alarm.component';
import { CommonsModule } from '../commons/commons.module';
import { FormsModule } from '@angular/forms';
import { AlarmDetailComponent } from './detail/detail.component';
import { PeriodSelectorComponent } from './period-selector/period-selector.component';


@NgModule({
  declarations: [
    AlarmComponent,
    AlarmDetailComponent,
    PeriodSelectorComponent
  ],
  imports: [
    CommonModule,
    AlarmRoutingModule,
    CommonsModule,
    FormsModule
  ]
})
export class AlarmModule { }
