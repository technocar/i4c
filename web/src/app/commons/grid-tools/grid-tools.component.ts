import { Component, EventEmitter, OnInit, Output } from '@angular/core';

@Component({
  selector: 'app-grid-tools',
  templateUrl: './grid-tools.component.html',
  styleUrls: ['./grid-tools.component.scss']
})
export class GridToolsComponent implements OnInit {

  @Output("reload") reload: EventEmitter<void> = new EventEmitter();

  constructor() { }

  ngOnInit(): void {
  }

  doReload() {
    this.reload.emit();
  }
}
