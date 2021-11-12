import { AuthenticationInterceptor } from './services/auth.interceptor';

import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { HttpClientModule, HTTP_INTERCEPTORS } from '@angular/common/http';

import { AppRoutingModule } from './app-routing.module';
import { AppComponent } from './app.component';
import { RouterModule } from '@angular/router';
import { DashboardComponent } from './dashboard/dashboard.component';
import { NgbAccordion, NgbCollapse, NgbModule } from '@ng-bootstrap/ng-bootstrap';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { SelectorComponent } from './selector/selector.component';
import { AuthGuard } from './services/auth.guard';
import { LoginComponent } from './login/login.component';
import { CommonModule } from '@angular/common';
import { SnapshotBaseComponent } from './snapshots/snapshot-base/snapshot-base.component';
import { SnapshotMillComponent } from './snapshots/snapshot-mill/snapshot-mill.component';
import { SnapshotLatheComponent } from './snapshots/snapshot-lathe/snapshot-lathe.component';
import { SnapshotRobotComponent } from './snapshots/snapshot-robot/snapshot-robot.component';
import { SnapshotGomComponent } from './snapshots/snapshot-gom/snapshot-gom.component';
import { ProjectComponent } from './project/project.component';
import { AppHeaderComponent } from './app-header/app-header.component';
import { WorkPieceComponent } from './workpiece/list/workpiece.component';
import { WorkPieceStatus } from './services/models/api';
import { WorkpieceDetailComponent } from './workpiece/workpiece-detail/workpiece-detail.component';
import { WorkpieceDetailResolver } from './workpiece/workpiece-detail/workpiece-detail.resolver';

@NgModule({
  declarations: [
    AppComponent,
    SnapshotBaseComponent,
    SnapshotMillComponent,
    SnapshotLatheComponent,
    SnapshotRobotComponent,
    SnapshotGomComponent,
    DashboardComponent,
    SelectorComponent,
    LoginComponent,
    ProjectComponent,
    WorkPieceComponent,
    WorkpieceDetailComponent,
    AppHeaderComponent
  ],
  imports: [
    BrowserModule,
    CommonModule,
    HttpClientModule,
    AppRoutingModule,
    ReactiveFormsModule,
    FormsModule,
    NgbModule,
    RouterModule.forRoot([
      { path: 'workpiece',  children: [
        { path: 'list', component: WorkPieceComponent, canActivate: [AuthGuard] },
        { path: 'detail/:id', component: WorkpieceDetailComponent, canActivate: [AuthGuard], resolve: { data: WorkpieceDetailResolver } },
        { path: '', redirectTo: 'list', pathMatch: "full"  }
      ]},
      { path: 'workpiece', component: WorkPieceComponent, canActivate: [AuthGuard] },
      { path: 'project', component: ProjectComponent, canActivate: [AuthGuard] },
      { path: 'dashboard', component: DashboardComponent, canActivate: [AuthGuard] },
      { path: 'selector', component: SelectorComponent, canActivate: [AuthGuard] },
      { path: 'login', component: LoginComponent },
      { path: '', redirectTo: 'selector', pathMatch: "full" }
    ])
  ],
  exports: [RouterModule],
  providers: [
    { provide: HTTP_INTERCEPTORS, useClass: AuthenticationInterceptor, multi: true }
  ],
  bootstrap: [AppComponent]
})
export class AppModule { }
