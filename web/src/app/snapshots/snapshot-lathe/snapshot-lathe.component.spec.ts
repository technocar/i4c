import { ComponentFixture, TestBed } from '@angular/core/testing';

import { SnapshotLatheComponent } from './snapshot-lathe.component';

describe('SnapshotLatheComponent', () => {
  let component: SnapshotLatheComponent;
  let fixture: ComponentFixture<SnapshotLatheComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ SnapshotLatheComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(SnapshotLatheComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
