import { TestBed } from '@angular/core/testing';

import { WorkpieceDetailResolver } from './workpiece-detail.resolver';

describe('WorkpieceDetailResolver', () => {
  let resolver: WorkpieceDetailResolver;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    resolver = TestBed.inject(WorkpieceDetailResolver);
  });

  it('should be created', () => {
    expect(resolver).toBeTruthy();
  });
});
