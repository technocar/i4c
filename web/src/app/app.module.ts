import { AuthenticationInterceptor } from './services/auth.interceptor';

import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { HttpClientModule, HTTP_INTERCEPTORS } from '@angular/common/http';

import { AppRoutingModule } from './app-routing.module';
import { AppComponent } from './app.component';
import { RouterModule } from '@angular/router';
import { DashboardComponent } from './dashboard/dashboard.component';
import { NgbModule } from '@ng-bootstrap/ng-bootstrap';
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
      { path: 'project', component: ProjectComponent, canActivate: [AuthGuard] },
      { path: 'dashboard', component: DashboardComponent, canActivate: [AuthGuard] },
      { path: 'selector', component: SelectorComponent, canActivate: [AuthGuard] },
      { path: 'login', component: LoginComponent },
      { path: '', redirectTo: 'selector', pathMatch: "full" }
    ])
  ],
  providers: [
    { provide: HTTP_INTERCEPTORS, useClass: AuthenticationInterceptor, multi: true }
  ],
  bootstrap: [AppComponent]
})
export class AppModule { }
