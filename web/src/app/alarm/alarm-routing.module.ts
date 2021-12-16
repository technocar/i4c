import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { AuthGuard } from '../services/auth.guard';
import { AlarmComponent } from './alarm.component';
import { AlarmDetailResolver } from './detail/alarm-detail.resolver';
import { AlarmDetailComponent } from './detail/detail.component';

const routes: Routes = [{
  path: '',
  children: [
    { path: '', component: AlarmComponent, canActivate: [AuthGuard] },
    { path: ':name', component: AlarmDetailComponent, canActivate: [AuthGuard],
      resolve: { data: AlarmDetailResolver },
      data: { breadcrumb: (data: any) => `${data.data?.length > 0 ? data.data[0].name : "???"}` }
    }
  ],
  data: { breadcrumb: 'Riasztások' }
}];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule]
})
export class AlarmRoutingModule { }
