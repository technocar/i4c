import { TestBed } from '@angular/core/testing';

import { AnalysisResolver } from './analysis.resolver';

describe('AnalysisResolver', () => {
  let resolver: AnalysisResolver;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    resolver = TestBed.inject(AnalysisResolver);
  });

  it('should be created', () => {
    expect(resolver).toBeTruthy();
  });
});
