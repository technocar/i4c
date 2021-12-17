import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule } from '@angular/router';
import { FilterControlComponent } from './filter/filter.component';
import { FormsModule } from '@angular/forms';
import { NgbAlertModule, NgbButtonsModule, NgbDropdownModule, NgbPopoverModule, NgbTypeaheadModule } from '@ng-bootstrap/ng-bootstrap';
import { MetaFilterComponent } from './meta-filter/meta-filter.component';
import { MetaSelectorComponent } from './meta-selector/meta-selector.component';
import { GridToolsComponent } from './grid-tools/grid-tools.component';
import { AppNotifComponent } from './app-notif/app-notif.component';
import { AutocompleteInputComponent } from './autocomplete-input/autocomplete-input.component';



@NgModule({
  declarations: [
    FilterControlComponent,
    MetaFilterComponent,
    MetaSelectorComponent,
    GridToolsComponent,
    AppNotifComponent,
    AutocompleteInputComponent
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
    FilterControlComponent,
    MetaFilterComponent,
    MetaSelectorComponent,
    GridToolsComponent,
    AppNotifComponent,
    AutocompleteInputComponent
  ]
})
export class CommonsModule { }
