import { Injectable } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';

@Injectable({
  providedIn: 'root'
})
export class FiltersService {

  constructor(
    private router: Router,
    private route: ActivatedRoute
  ) { }

  read(name: string, filters: object) {
    var saveFilters = JSON.parse(sessionStorage.getItem(name));
    if ((saveFilters ?? null) !== null)
      Object.assign(filters, saveFilters);

    if (this.route && this.router) {
      for (let p in filters) {
        if (this.route.snapshot.queryParamMap.keys.indexOf(p) > -1)
          filters[p] = this.route.snapshot.queryParamMap.get(p);
      }
      this.save(name, filters);
    }
  }

  save(name: string, filters: object) {
    if ((filters ?? null) === null) {
      sessionStorage.removeItem(name);
      return;
    }
    sessionStorage.setItem(name, JSON.stringify(filters));

    this._saveToQueryParams(filters);
  }

  private _saveToQueryParams(filters: Object) {
    if (!this.route || !this.router)
      return;

    this.router.navigate([], {
      relativeTo: this.route,
      queryParams: filters,
      queryParamsHandling: 'merge'
    });
  }
}
