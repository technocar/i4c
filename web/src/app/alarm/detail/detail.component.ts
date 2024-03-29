import { Component, OnInit } from '@angular/core';
import { NgForm } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { BehaviorSubject } from 'rxjs';
import { ApiService } from 'src/app/services/api.service';
import { Alarm, AlarmGroup, AlarmRule, AlarmRuleSampleAggMethod, Device, Meta, NumberRelation, StringRelation } from 'src/app/services/models/api';
import { DeviceType, Labels } from 'src/app/services/models/constants';
import { AppNotifType, NotificationService } from 'src/app/services/notification.service';

interface Rule extends AlarmRule {
  id: number,
  device: DeviceType,
  value_list: string[]
}

@Component({
  selector: 'app-detail',
  templateUrl: './detail.component.html',
  styleUrls: ['./detail.component.scss']
})
export class AlarmDetailComponent implements OnInit {

  origDef: Alarm;
  def: Alarm;
  rules$: BehaviorSubject<Rule[]> = new BehaviorSubject([]);
  devices: Device[] = [];
  metaList: Meta[];
  groups: string[];
  pattern: '^$|^[^:/?&+=a]+$';

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private apiService: ApiService,
    private notifService: NotificationService
  ) { }

  ngOnInit(): void {
    this.apiService.getDevices().subscribe(r => this.devices = r);

    this.route.data.subscribe(r => {
      this.def = r.data[0] as Alarm;
      this.origDef = this.def;
      this.metaList = r.data[1] as Meta[];
      this.rules$.next(this.def.conditions.map((r, idx) => {
        var device = (r.condition ?? r.event ?? r.sample).device;
        var rule = Object.assign({ device: device, value_list: [], id: idx + 1 }, r);
        return rule;
      }));
      this.groups = (<AlarmGroup[]>(r.data[2] ?? [])).map(g => g.name);
    });
  }

  getPeriods(): string[][] {
    return Labels.periods.filter(p => p[0] !== "Y");
  }

  getNumberAggregates(): string[][] {
    return [
      [AlarmRuleSampleAggMethod.Avg, $localize `:@@alarm_rule_sample_aggmethod__avg:átlag`],
      [AlarmRuleSampleAggMethod.Median, $localize `:@@alarm_rule_sample_aggmethod__median:medián`],
      [AlarmRuleSampleAggMethod.Q1th, $localize `:@@alarm_rule_sample_aggmethod__q1th:1. kvintilis`],
      [AlarmRuleSampleAggMethod.Q4th, $localize `:@@alarm_rule_sample_aggmethod__q1th:4. kvintilis`],
      [AlarmRuleSampleAggMethod.Slope, $localize `:@@alarm_rule_sample_aggmethod__slope:slope`]
    ];
  }

  getNumberRelations(): string[] {
    return [
      NumberRelation.Equal,
      NumberRelation.NotEqual,
      NumberRelation.Greater,
      NumberRelation.GreaterEqual,
      NumberRelation.Lesser,
      NumberRelation.LesserEqual
    ]
  }

  getStringRelations(): string[] {
    return [
      StringRelation.Equal,
      StringRelation.NotEqual,
      StringRelation.Contains,
      StringRelation.NotContains
    ];
  }

  getMetaForDevice(device: DeviceType): Meta[] {
    return this.metaList.filter(m => m.device === device);
  }

  getSelectedDataId(rule: Rule) {
    return (rule.sample ?? rule.event ?? rule.condition)?.data_id ?? undefined;
  }

  selectRuleMeta(rule: Rule, meta: Meta) {
    switch (meta.category) {
      case "EVENT":
        rule.value_list = meta.value_list ?? [];
        rule.condition = undefined;
        rule.sample = undefined;
        if (!rule.event)
          rule.event = {
            device: rule.device,
            data_id: meta.data_id,
            rel: StringRelation.Equal
          };
        else
          rule.event.data_id = meta.data_id;
        break;
      case "SAMPLE":
        rule.condition = undefined;
        rule.event = undefined;
        if (!rule.sample)
          rule.sample = {
            device: rule.device,
            data_id: meta.data_id,
            rel: NumberRelation.Equal
          };
        else
          rule.sample.data_id = meta.data_id;
        break;
      case "CONDITION":
        rule.event = undefined;
        rule.sample = undefined;
        if (!rule.condition)
          rule.condition = {
            device: rule.device,
            data_id: meta.data_id,
          }
        else
          rule.condition.data_id = meta.data_id;
        break;
      default:
        break;
    }
  }

  trackByRuleIdx(index: number, rule: Rule) {
    return rule.id;
  }

  changeRuleDevice(rule: Rule, event: Event) {
    rule.device = (event.target as HTMLSelectElement).value as DeviceType;
  }

  newRule() {
    this.rules$.value.push({
      id: (this.rules$.value.length === 0 ? 0 : Math.max(...this.rules$.value.map(f => f.id))) + 1,
      device: DeviceType.Lathe,
      value_list: [],
      condition: undefined,
      event: undefined,
      sample: undefined
    });
    console.log(this.rules$.value);
  }

  deleteRule(id: number) {
    var rules = this.rules$.value;
    var index = rules.findIndex(r => r.id === id);
    if (index > -1)
      rules.splice(index, 1);
    this.rules$.next(rules);
  }

  save(form: NgForm) {
    if (form.invalid)
      return;

    this.apiService.setAlarm(encodeURIComponent(this.origDef.name), this.def)
      .subscribe(r => {
        this.router.navigate(['def', r.name], { relativeTo: this.route.parent, replaceUrl: true });
        this.notifService.sendAppNotif(AppNotifType.Success, $localize `:@@save_success:Sikeres mentés!`);
      }, err => {
        this.notifService.sendAppNotif(AppNotifType.Error, this.apiService.getErrorMsg(err).toString());
      });
  }
}
