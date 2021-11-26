import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { AuthGuard } from '../services/auth.guard';
import { AnalysesComponent } from './analyses.component';
import { AnalysisComponent } from './analysis/analysis.component';
import { AnalysisResolver } from './analysis/analysis.resolver';

const routes: Routes = [
  { path: '',
    children: [
      { path: '', component: AnalysesComponent, canActivate: [AuthGuard] },
      { path: ':id', component: AnalysisComponent, canActivate: [AuthGuard],
        resolve: { data: AnalysisResolver },
        data: { breadcrumb: (data: any) => `${(data.data ?? []).length > 2 ? data.data[1].name : "???"}` }
      }
    ],
    data: { breadcrumb: 'Adatelemzések' }
  },
];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule]
})
export class AnalysesRoutingModule { }
