import { NgModule } from '@angular/core';
import { RouterModule, Routes } from '@angular/router';
import { AuthGuard } from '../services/auth.guard';
import { AlarmComponent } from './alarm.component';
import { AlarmDetailResolver } from './detail/alarm-detail.resolver';
import { AlarmDetailComponent } from './detail/detail.component';
import { AlarmSubscriptionDetailResolver } from './subscription/detail/detail-resolver.resolver';
import { AlarmSubscriptionDetailComponent } from './subscription/detail/detail.component';
import { AlarmSubscriptionComponent } from './subscription/subscription.component';

const routes: Routes = [{
  path: '',
  children: [
    { path: 'subscriptions', data: { breadcrumb: 'Feliratkozások', priv: "get/alarm/subs" },
      children: [{
        path: ':user/:id', component: AlarmSubscriptionDetailComponent, canActivate: [AuthGuard],
        resolve: { data: AlarmSubscriptionDetailResolver },
        data: {
          breadcrumb: (data: any) => `${data.data?.length > 0 ? data.data[0].address_name : "???"}`,
          priv: "get/alarm/subs/{id}"
       }
      },
      { path: '', component: AlarmSubscriptionComponent, canActivate: [AuthGuard], data: { priv: "get/alarm/subs" } }]
    },
    { path: 'def/:name', component: AlarmDetailComponent, canActivate: [AuthGuard],
      resolve: { data: AlarmDetailResolver },
      data: {
        breadcrumb: (data: any) => `${data.data?.length > 0 ? data.data[0].name : "???"}`,
        priv: "get/alarm/defs/{name}"
      }
    },
    { path: 'create', component: AlarmDetailComponent, canActivate: [AuthGuard],
      resolve: { data: AlarmDetailResolver },
      data: {
        breadcrumb: (data: any) => `<új riasztás>`,
        priv: "get/alarm/defs/{name}"
      }
    },
    { path: '', component: AlarmComponent, canActivate: [AuthGuard], data: { priv: "get/alarm/defs" } }
  ],
  data: { breadcrumb: 'Riasztások' }
}];

@NgModule({
  imports: [RouterModule.forChild(routes)],
  exports: [RouterModule]
})
export class AlarmRoutingModule { }
