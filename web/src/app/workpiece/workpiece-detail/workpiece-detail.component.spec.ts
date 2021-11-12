import { ComponentFixture, TestBed } from '@angular/core/testing';

import { WorkpieceDetailComponent } from './workpiece-detail.component';

describe('WorkpieceDetailComponent', () => {
  let component: WorkpieceDetailComponent;
  let fixture: ComponentFixture<WorkpieceDetailComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ WorkpieceDetailComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(WorkpieceDetailComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
