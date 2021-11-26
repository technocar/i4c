import { ComponentFixture, TestBed } from '@angular/core/testing';

import { MetaSelectorComponent } from './meta-selector.component';

describe('MetaSelectorComponent', () => {
  let component: MetaSelectorComponent;
  let fixture: ComponentFixture<MetaSelectorComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ MetaSelectorComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(MetaSelectorComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
