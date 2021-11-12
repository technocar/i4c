import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { AuthGuard } from '../services/auth.guard';
import { WorkPieceComponent } from './list/workpiece.component';
import { WorkpieceDetailComponent } from './workpiece-detail/workpiece-detail.component';
import { WorkpieceDetailResolver } from './workpiece-detail/workpiece-detail.resolver';

const routes: Routes = [
  { path: 'list', component: WorkPieceComponent, canActivate: [AuthGuard] },
  { path: 'detail/:id', component: WorkpieceDetailComponent, canActivate: [AuthGuard], resolve: { data: WorkpieceDetailResolver } },
  { path: '', redirectTo: 'list', pathMatch: "full"  }
];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule]
})
export class WorkPieceRoutingModule { }
