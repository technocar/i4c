import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { AppHeaderComponent } from './app-header/app-header.component';
import { RouterModule } from '@angular/router';
import { FilterControlComponent } from './filter/filter.component';
import { FormsModule } from '@angular/forms';
import { NgbPopoverModule } from '@ng-bootstrap/ng-bootstrap';



@NgModule({
  declarations: [
    AppHeaderComponent,
    FilterControlComponent
  ],
  imports: [
    CommonModule,
    RouterModule,
    FormsModule,
    NgbPopoverModule
  ],
  exports: [
    AppHeaderComponent,
    FilterControlComponent
  ]
})
export class CommonsModule { }
