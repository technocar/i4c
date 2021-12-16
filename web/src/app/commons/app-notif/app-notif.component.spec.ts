import { ComponentFixture, TestBed } from '@angular/core/testing';

import { AppNotifComponent } from './app-notif.component';

describe('AppNotifComponent', () => {
  let component: AppNotifComponent;
  let fixture: ComponentFixture<AppNotifComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ AppNotifComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(AppNotifComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
