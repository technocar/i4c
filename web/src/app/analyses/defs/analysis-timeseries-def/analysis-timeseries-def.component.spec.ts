import { ComponentFixture, TestBed } from '@angular/core/testing';

import { AnalysisTimeseriesDefComponent } from './analysis-timeseries-def.component';

describe('AnalysisTimeseriesDefComponent', () => {
  let component: AnalysisTimeseriesDefComponent;
  let fixture: ComponentFixture<AnalysisTimeseriesDefComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ AnalysisTimeseriesDefComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(AnalysisTimeseriesDefComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
