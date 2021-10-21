import { ComponentFixture, TestBed } from '@angular/core/testing';

import { SnapshotGomComponent } from './snapshot-gom.component';

describe('SnapshotGomComponent', () => {
  let component: SnapshotGomComponent;
  let fixture: ComponentFixture<SnapshotGomComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ SnapshotGomComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(SnapshotGomComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
