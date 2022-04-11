import { Component, OnInit } from '@angular/core';
import { AbstractControl, FormControl, FormGroup, ValidationErrors, ValidatorFn, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { ApiService } from 'src/app/services/api.service';

export function matchValidator(
  matchTo: string,
  reverse?: boolean
): ValidatorFn {
  return (control: AbstractControl):
  ValidationErrors | null => {
    if (control.parent && reverse) {
      const c = (control.parent?.controls as any)[matchTo] as AbstractControl;
      if (c) {
        c.updateValueAndValidity();
      }
      return null;
    }
    return !!control.parent &&
      !!control.parent.value &&
      control.value ===
      (control.parent?.controls as any)[matchTo].value
      ? null
      : { matching: true };
  };
}

@Component({
  selector: 'app-password-reset',
  templateUrl: './password-reset.component.html',
  styleUrls: ['./password-reset.component.scss']
})
export class PasswordResetComponent implements OnInit {

  form: FormGroup;
  get f() { return this.form.controls; }
  submitted: boolean = false;
  loading: boolean = false;
  error: string = undefined;
  username: string = undefined;
  private token: string = undefined;

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private apiService: ApiService
  ) {
    this.username = route.snapshot.queryParamMap.get("login");
    this.token = route.snapshot.paramMap.get("token");
  }

  ngOnInit(): void {
    this.form = new FormGroup({
      password: new FormControl('', Validators.compose([
        Validators.required,
        Validators.minLength(6),
        Validators.pattern('^(?=.*[a-z])(?=.*[A-Z])(?=.*[0-9])[a-zA-Z0-9]+$'),
        matchValidator('password2', true)
      ])),
      password2: new FormControl('', [
        Validators.required,
        matchValidator('password')
      ])
    });
  }

  onSubmit() {
    this.submitted = true;

    if (this.form.invalid)
      return;

    var password = this.form.controls.password.value
    var password2 = this.form.controls.password2.value;

    if (password !== password2)
      return;

    this.loading = true;
    this.apiService.setNewPassword(this.username, this.token, password)
      .subscribe(r => {
        this.router.navigate(['/login']);
      }, err => {
        this.error = this.apiService.getErrorMsg(err).toString();
      }, () => {
        this.loading = false;
      });
  }


}
