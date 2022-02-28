import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { AuthGuard } from '../services/auth.guard';
import { AnalysesComponent } from './analyses.component';
import { AnalysisComponent } from './analysis/analysis.component';
import { AnalysisResolver } from './analysis/analysis.resolver';


const routes: Routes = [
  { path: '',
    children: [
      { path: '', component: AnalysesComponent, canActivate: [AuthGuard], data: { priv: "get/stat/def" } },
      { path: ':id', component: AnalysisComponent, canActivate: [AuthGuard],
        resolve: { data: AnalysisResolver },
        data: {
          breadcrumb: (data: any) => `${(data.data ?? []).length > 1 ? data.data[0]?.name + " (" + data.data[3] + ")" ?? "Új elemzés" : "???"}`,
          data: { priv: "get/stat/def/{id}" }
        }
      },
      { path: ':id/:type/:caption', component: AnalysisComponent, canActivate: [AuthGuard],
        resolve: { data: AnalysisResolver },
        data: {
          breadcrumb: (data: any) => `${(data.data ?? []).length > 1 ? data.data[0]?.name ?? "Új elemzés" : "???"}`,
          data: { priv: "get/stat/def/{id}" }
        }
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
