import { TestBed } from '@angular/core/testing';

import { AlarmDetailResolver } from './alarm-detail.resolver';

describe('AlarmDetailResolver', () => {
  let resolver: AlarmDetailResolver;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    resolver = TestBed.inject(AlarmDetailResolver);
  });

  it('should be created', () => {
    expect(resolver).toBeTruthy();
  });
});
