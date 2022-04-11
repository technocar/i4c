import { Component, EventEmitter, Input, OnInit, Output, ViewChild } from '@angular/core';
import { NgbTypeahead } from '@ng-bootstrap/ng-bootstrap';
import { merge, Observable, OperatorFunction, Subject } from 'rxjs';
import { debounceTime, distinctUntilChanged, map } from 'rxjs/operators';

@Component({
  selector: 'autocomplete-input',
  templateUrl: './autocomplete-input.component.html',
  styleUrls: ['./autocomplete-input.component.scss']
})
export class AutocompleteInputComponent implements OnInit {

  @Input() values: string[] = [];
  @Input() value: string;
  @Input() disabled: boolean = false;
  @Output() valueChange: EventEmitter<string> = new EventEmitter();

  @ViewChild('valuesSelector', {static: true}) instance: NgbTypeahead;

  focus$ = new Subject<string>();
  click$ = new Subject<string>();

  constructor() { }

  ngOnInit(): void {
  }

  search: OperatorFunction<string, readonly string[]> = (text$: Observable<string>) => {
    const debouncedText$ = text$.pipe(debounceTime(200), distinctUntilChanged());
    const clicksWithClosedPopup$ = this.click$;
    const inputFocus$ = this.focus$;

    return merge(debouncedText$, inputFocus$, clicksWithClosedPopup$).pipe(
      map(term => (term === '' ? (this.values ?? [])
        : (this.values ?? []).filter(v => v.toLowerCase().indexOf(term.toLowerCase()) > -1)).slice(0, 10))
    );
  }

  change(value: string) {
    this.valueChange.next(value);
  }
}
