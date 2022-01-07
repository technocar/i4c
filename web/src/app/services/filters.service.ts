import { Injectable } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { Location } from '@angular/common';

@Injectable({
  providedIn: 'root'
})
export class FiltersService {

  constructor(
    private router: Router,
    private route: ActivatedRoute,
    private location: Location
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
    if (!this.route || !this.router || !this.location || (filters ?? undefined) === undefined)
      return;

  let urlTree = this.router.parseUrl(this.router.url);
  urlTree.queryParams = {};

  this.location.replaceState(urlTree.toString(), Object.keys(filters).filter(key => (filters[key] ?? null) !== null).map(key => key + '=' + filters[key]).join('&'));
  }
}
