import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { PasswordResetComponent } from './password-reset/password-reset.component';

const routes: Routes = [{
  path: '',
  children: [
    {path: 'passwordreset/:token', component: PasswordResetComponent, data: { breadcrumb: "új jelszó" }}
  ]
}];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule]
})
export class ProfileRoutingModule { }
