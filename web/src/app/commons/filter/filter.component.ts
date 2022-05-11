import { Component, EventEmitter, Input, OnInit, Output, ViewEncapsulation } from '@angular/core';

@Component({
  selector: 'ctrl-filter',
  templateUrl: './filter.component.html',
  styleUrls: ['./filter.component.scss'],
  encapsulation: ViewEncapsulation.None
})
export class FilterControlComponent implements OnInit {

  @Input("name") name: string;
  @Input("id") id: string;
  @Input() value: any;
  @Output() valueChange: EventEmitter<any> = new EventEmitter<any>();
  @Input("css") css: string;
  @Input("mask") mask: boolean;
  @Input("queryParam")
  @Output("change") change: EventEmitter<any> = new EventEmitter<any>();
  get queryParam(): string {
    return this.value ? (this.mask ? `#|${this.value}|` : this.value) : undefined;
  }
  set queryParam(value: string) {
    this.mask = false;
    this.value = undefined;
    if (value === undefined || value === null)
      return;

    if (value.startsWith("#|") && value.endsWith("|")) {
      this.mask = true;
      value = value.substr(2);

      if (value.endsWith("|"))
        value = value.substr(0, value.length - 1);
    }

    this.value = (value ?? "") === "" ? undefined : value;
  }

  constructor() { }

  ngOnInit(): void {
  }

  filter() {
    this.valueChange.emit((this.value ?? "") === "" ? undefined : this.value);
    this.change.emit((this.value ?? "") === "" ? undefined : this.value);
  }
}
