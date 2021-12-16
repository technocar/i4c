import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { AppHeaderComponent } from './app-header/app-header.component';
import { RouterModule } from '@angular/router';
import { FilterControlComponent } from './filter/filter.component';
import { FormsModule } from '@angular/forms';
import { NgbAlertModule, NgbButtonsModule, NgbDropdownModule, NgbPopoverModule, NgbTypeaheadModule } from '@ng-bootstrap/ng-bootstrap';
import { MetaFilterComponent } from './meta-filter/meta-filter.component';
import { MetaSelectorComponent } from './meta-selector/meta-selector.component';
import { GridToolsComponent } from './grid-tools/grid-tools.component';
import { AppNotifComponent } from './app-notif/app-notif.component';



@NgModule({
  declarations: [
    AppHeaderComponent,
    FilterControlComponent,
    MetaFilterComponent,
    MetaSelectorComponent,
    GridToolsComponent,
    AppNotifComponent
  ],
  imports: [
    CommonModule,
    RouterModule,
    FormsModule,
    NgbPopoverModule,
    NgbTypeaheadModule,
    NgbAlertModule,
    NgbDropdownModule,
    NgbButtonsModule
  ],
  exports: [
    AppHeaderComponent,
    FilterControlComponent,
    MetaFilterComponent,
    MetaSelectorComponent,
    GridToolsComponent,
    AppNotifComponent
  ]
})
export class CommonsModule { }
