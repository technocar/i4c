import { Component, OnInit, TemplateRef, ViewChild } from '@angular/core';
import { Router, ActivatedRoute } from '@angular/router';
import { FormBuilder, FormGroup, Validators  } from '@angular/forms';
import { AuthenticationService } from '../services/auth.service';
import { ApiService } from '../services/api.service';
import { NgbActiveModal, NgbModal } from '@ng-bootstrap/ng-bootstrap';

@Component({
  selector: 'app-login',
  templateUrl: './login.component.html',
  styleUrls: ['./login.component.scss']
})
export class LoginComponent implements OnInit {
  loginForm: FormGroup;
  loading = false;
  submitted = false;
  returnUrl: string;
  error = '';
  message = '';
  dialogSubmitted = false;

  @ViewChild("forgottenPasswordDialog") fpDialog;
  private activeModal: NgbActiveModal;

  constructor(
    private formBuilder: FormBuilder,
    private route: ActivatedRoute,
    private router: Router,
    private authenticationService: AuthenticationService,
    private apiService: ApiService,
    private modalService: NgbModal
  ) {
    // redirect to home if already logged in
    if (this.authenticationService.isAuthenticated()) {
      this.router.navigate(['/']);
    }
  }

  ngOnInit() {
    this.loginForm = this.formBuilder.group({
      username: ['', Validators.required],
      password: ['', Validators.required]
    });

    // get return url from route parameters or default to '/'
    this.returnUrl = this.route.snapshot.queryParams['returnUrl'] || '/';
  }

  // convenience getter for easy access to form fields
  get f() { return this.loginForm.controls; }

  onSubmit() {
    this.error = '';
    this.message = '';
    this.submitted = true;

    // stop here if form is invalid
    if (this.loginForm.invalid) {
      return;
    }

    this.loading = true;
    this.authenticationService.login(this.f.username.value, this.f.password.value)
      .subscribe(
        user => {
          this.router.navigateByUrl(this.returnUrl);
        },
        error => {
          this.error = this.apiService.getErrorMsg(error).toString();
          this.loading = false;
          this.authenticationService.removeUser();
        });
  }

  showNewPasswordDialog() {
    this.activeModal = this.modalService.open(this.fpDialog);
  }

  requestNewPassword(username: string) {
    this.message = '';
    this.error = '';

    this.dialogSubmitted = true;

    if (!username)
      return;

    this.activeModal.close();

    this.apiService.requestNewPassword(username)
      .subscribe(r => {
        this.message = $localize `:@@login_request_new_password_ok:Jelszó változtatás link elküldve az ön email címére.`;
      }, err => {
        this.error = this.apiService.getErrorMsg(err).toString();
      });
  }
}
