import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { AppHeaderComponent } from './app-header/app-header.component';
import { RouterModule } from '@angular/router';



@NgModule({
  declarations: [
    AppHeaderComponent
  ],
  imports: [
    CommonModule,
    RouterModule
  ],
  exports: [
    AppHeaderComponent
  ]
})
export class CommonsModule { }
