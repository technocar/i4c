import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { AuthGuard } from '../services/auth.guard';
import { ProjectComponent } from './project.component';
import { ProjectResolver } from './project.resolver';

const routes: Routes = [
  { path: '', component: ProjectComponent, canActivate: [AuthGuard], resolve: { data: ProjectResolver }, data: { breadcrumb: "Telepítés" } }
];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule]
})
export class ProjectRoutingModule { }
