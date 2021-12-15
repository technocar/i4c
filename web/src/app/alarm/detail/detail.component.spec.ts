import { ComponentFixture, TestBed } from '@angular/core/testing';

import { AlarmDetailComponent } from './detail.component';

describe('DetailComponent', () => {
  let component: AlarmDetailComponent;
  let fixture: ComponentFixture<AlarmDetailComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ AlarmDetailComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(AlarmDetailComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
