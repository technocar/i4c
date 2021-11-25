import { ComponentFixture, TestBed } from '@angular/core/testing';

import { AnalysisDatetimeDefComponent } from './analysis-datetime-def.component';

describe('AnalysisDatetimeDefComponent', () => {
  let component: AnalysisDatetimeDefComponent;
  let fixture: ComponentFixture<AnalysisDatetimeDefComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ AnalysisDatetimeDefComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(AnalysisDatetimeDefComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
