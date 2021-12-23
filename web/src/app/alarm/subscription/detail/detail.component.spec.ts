import { ComponentFixture, TestBed } from '@angular/core/testing';

import { AlarmSubscriptionDetailComponent } from './detail.component';

describe('DetailComponent', () => {
  let component: AlarmSubscriptionDetailComponent;
  let fixture: ComponentFixture<AlarmSubscriptionDetailComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ AlarmSubscriptionDetailComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(AlarmSubscriptionDetailComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
