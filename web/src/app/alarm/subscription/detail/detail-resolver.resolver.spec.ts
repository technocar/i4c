import { TestBed } from '@angular/core/testing';

import { AlarmSubscriptionDetailResolver } from './detail-resolver.resolver';

describe('DetailResolverResolver', () => {
  let resolver: AlarmSubscriptionDetailResolver;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    resolver = TestBed.inject(AlarmSubscriptionDetailResolver);
  });

  it('should be created', () => {
    expect(resolver).toBeTruthy();
  });
});
