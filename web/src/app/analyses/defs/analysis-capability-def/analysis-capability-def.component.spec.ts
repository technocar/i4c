import { ComponentFixture, TestBed } from '@angular/core/testing';

import { AnalysisCapabilityDefComponent } from './analysis-capability-def.component';

describe('AnalysisCapabilityDefComponent', () => {
  let component: AnalysisCapabilityDefComponent;
  let fixture: ComponentFixture<AnalysisCapabilityDefComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ AnalysisCapabilityDefComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(AnalysisCapabilityDefComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
