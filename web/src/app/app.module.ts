import { AuthenticationInterceptor } from './services/auth.interceptor';

import { NgModule } from '@angular/core';
import { BrowserModule } from '@angular/platform-browser';
import { HttpClientModule, HTTP_INTERCEPTORS } from '@angular/common/http';

import { AppRoutingModule } from './app-routing.module';
import { AppComponent } from './app.component';
import { RouterModule } from '@angular/router';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { SelectorComponent } from './selector/selector.component';
import { AuthGuard } from './services/auth.guard';
import { LoginComponent } from './login/login.component';
import { CommonModule } from '@angular/common';
import { CommonsModule } from './commons/commons.module';
import { NgbDropdownModule, NgbProgressbarModule } from '@ng-bootstrap/ng-bootstrap';
import { QuillModule } from 'ngx-quill';

@NgModule({
  declarations: [
    AppComponent,
    SelectorComponent,
    LoginComponent
  ],
  imports: [
    BrowserModule,
    CommonModule,
    HttpClientModule,
    AppRoutingModule,
    ReactiveFormsModule,
    FormsModule,
    CommonsModule,
    NgbProgressbarModule,
    NgbDropdownModule,
    QuillModule.forRoot(),
    RouterModule.forRoot([
      { path: 'workpiece', loadChildren: () => import('./workpiece/workpiece.module').then(m => m.WorkpieceModule), canActivate: [AuthGuard] },
      { path: 'project', loadChildren: () => import('./project/project.module').then(m => m.ProjectModule), canActivate: [AuthGuard] },
      { path: 'dashboard', loadChildren: () => import('./dashboard/dashboard.module').then(m => m.DashboardModule), canActivate: [AuthGuard] },
      { path: 'tools', loadChildren: () => import('./tools/tools.module').then(m => m.ToolsModule), canActivate: [AuthGuard] },
      { path: 'analyses', loadChildren: () => import('./analyses/analyses.module').then(m => m.AnalysesModule), canActivate: [AuthGuard] },
      { path: 'selector', component: SelectorComponent, canActivate: [AuthGuard], data: { breadcrumb: "Kezdőlap" } },
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
