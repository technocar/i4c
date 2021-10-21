import { ComponentFixture, TestBed } from '@angular/core/testing';

import { SnapshotBaseComponent } from './snapshot-base.component';

describe('SnapshotBaseComponent', () => {
  let component: SnapshotBaseComponent;
  let fixture: ComponentFixture<SnapshotBaseComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ SnapshotBaseComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(SnapshotBaseComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
