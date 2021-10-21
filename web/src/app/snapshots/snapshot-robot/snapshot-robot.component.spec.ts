import { ComponentFixture, TestBed } from '@angular/core/testing';

import { SnapshotRobotComponent } from './snapshot-robot.component';

describe('SnapshotRobotComponent', () => {
  let component: SnapshotRobotComponent;
  let fixture: ComponentFixture<SnapshotRobotComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ SnapshotRobotComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(SnapshotRobotComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
