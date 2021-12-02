import { ComponentFixture, TestBed } from '@angular/core/testing';

import { AnalysisXyDefComponent } from './analysis-xy-def.component';

describe('AnalysisXyDefComponent', () => {
  let component: AnalysisXyDefComponent;
  let fixture: ComponentFixture<AnalysisXyDefComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ AnalysisXyDefComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(AnalysisXyDefComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
