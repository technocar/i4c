import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';

import { AlarmRoutingModule } from './alarm-routing.module';
import { AlarmComponent } from './alarm.component';
import { CommonsModule } from '../commons/commons.module';
import { FormsModule } from '@angular/forms';
import { AlarmDetailComponent } from './detail/detail.component';
import { PeriodSelectorComponent } from './period-selector/period-selector.component';
import { NgbButtonsModule, NgbTypeaheadModule } from '@ng-bootstrap/ng-bootstrap';
import { AlarmSubscriptionComponent } from './subscription/subscription.component';
import { AlarmSubscriptionDetailComponent } from './subscription/detail/detail.component';


@NgModule({
  declarations: [
    AlarmComponent,
    AlarmDetailComponent,
    PeriodSelectorComponent,
    AlarmSubscriptionComponent,
    AlarmSubscriptionDetailComponent
  ],
  imports: [
    CommonModule,
    AlarmRoutingModule,
    CommonsModule,
    FormsModule,
    NgbTypeaheadModule,
    NgbButtonsModule
  ]
})
export class AlarmModule { }
