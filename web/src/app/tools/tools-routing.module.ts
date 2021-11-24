import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { AuthGuard } from '../services/auth.guard';
import { ToolDetailsComponent } from './tool-details/tool-details.component';
import { ToolsComponent } from './tools.component';

const routes: Routes = [
  { path: '',  children: [
    { path: '', component: ToolsComponent, canActivate: [AuthGuard] },
    { path: 'detail/:device/:ts/:seq', component: ToolDetailsComponent, canActivate: [AuthGuard] }
  ],
  data: { breadcrumb: "Eszközök" }}
];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule]
})
export class ToolsRoutingModule { }
