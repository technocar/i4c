import { Component, OnInit } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { Meta } from 'src/app/services/models/api';

@Component({
  selector: 'app-analysis',
  templateUrl: './analysis.component.html',
  styleUrls: ['./analysis.component.scss']
})
export class AnalysisComponent implements OnInit {

  metaList: Meta[] = [];

  constructor(
    private route: ActivatedRoute
  ) { }

  ngOnInit(): void {
    this.route.data.subscribe(r => {
      this.metaList = r.data[0];
    });

  }

}
