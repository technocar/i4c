import { ComponentFixture, TestBed } from '@angular/core/testing';

import { WorkPieceComponent } from './workpiece.component';

describe('WorkpieceComponent', () => {
  let component: WorkPieceComponent;
  let fixture: ComponentFixture<WorkPieceComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ WorkPieceComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(WorkPieceComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
