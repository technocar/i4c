import { ComponentFixture, TestBed } from '@angular/core/testing';

import { SnapshotMillComponent } from './snapshot-mill.component';

describe('SnapshotMillComponent', () => {
  let component: SnapshotMillComponent;
  let fixture: ComponentFixture<SnapshotMillComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ SnapshotMillComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(SnapshotMillComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
