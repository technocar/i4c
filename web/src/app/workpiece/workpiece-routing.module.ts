import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { AuthGuard } from '../services/auth.guard';
import { WorkPieceComponent } from './list/workpiece.component';
import { WorkpieceDetailComponent } from './workpiece-detail/workpiece-detail.component';
import { WorkpieceDetailResolver } from './workpiece-detail/workpiece-detail.resolver';

const routes: Routes = [
  { path: '',  children: [
    { path: '', component: WorkPieceComponent, canActivate: [AuthGuard], data: { priv: "get/workpiece" } },
    { path: 'detail/:id', component: WorkpieceDetailComponent, canActivate: [AuthGuard],
      resolve: { workpiece: WorkpieceDetailResolver },
      data: {
        breadcrumb: (data: any) => `${data.workpiece.id}`,
        data: { priv: "get/workpiece/{id}" }
      }
    }],
    data: { breadcrumb: "Munkaszámok" }
  }
];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule]
})
export class WorkPieceRoutingModule { }
