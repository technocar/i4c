import { ComponentFixture, TestBed } from '@angular/core/testing';

import { MetaFilterComponent } from './meta-filter.component';

describe('MetaFilterComponent', () => {
  let component: MetaFilterComponent;
  let fixture: ComponentFixture<MetaFilterComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ MetaFilterComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(MetaFilterComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
