import { ComponentFixture, TestBed } from '@angular/core/testing';

import { AnalysisListDefComponent } from './analysis-list-def.component';

describe('AnalysisListDefComponent', () => {
  let component: AnalysisListDefComponent;
  let fixture: ComponentFixture<AnalysisListDefComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      declarations: [ AnalysisListDefComponent ]
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(AnalysisListDefComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
