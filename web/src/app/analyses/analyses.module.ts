import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';

import { AnalysesRoutingModule } from './analyses-routing.module';
import { AnalysesComponent } from './analyses.component';
import { CommonsModule } from '../commons/commons.module';
import { FormsModule } from '@angular/forms';
import { NgbAccordionModule, NgbButtonsModule, NgbModalModule } from '@ng-bootstrap/ng-bootstrap';
import { AnalysisDatetimeDefComponent } from './defs/analysis-datetime-def/analysis-datetime-def.component';
import { AnalysisTimeseriesDefComponent } from './defs/analysis-timeseries-def/analysis-timeseries-def.component';
import { AnalysisComponent } from './analysis/analysis.component';
import { AnalysisXyDefComponent } from './defs/analysis-xy-def/analysis-xy-def.component';
import { QuillModule } from 'ngx-quill';

@NgModule({
  declarations: [
    AnalysesComponent,
    AnalysisDatetimeDefComponent,
    AnalysisTimeseriesDefComponent,
    AnalysisComponent,
    AnalysisXyDefComponent
  ],
  imports: [
    CommonModule,
    AnalysesRoutingModule,
    CommonsModule,
    FormsModule,
    NgbButtonsModule,
    NgbAccordionModule,
    NgbModalModule,
    QuillModule
  ]
})
export class AnalysesModule { }
