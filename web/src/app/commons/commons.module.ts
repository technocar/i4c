import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { AppHeaderComponent } from './app-header/app-header.component';
import { RouterModule } from '@angular/router';
import { FilterControlComponent } from './filter/filter.component';
import { FormsModule } from '@angular/forms';
import { NgbAlertModule, NgbButtonsModule, NgbDropdownModule, NgbPopoverModule, NgbTypeaheadModule } from '@ng-bootstrap/ng-bootstrap';
import { MetaFilterComponent } from './meta-filter/meta-filter.component';



@NgModule({
  declarations: [
    AppHeaderComponent,
    FilterControlComponent,
    MetaFilterComponent
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
    MetaFilterComponent
  ]
})
export class CommonsModule { }
