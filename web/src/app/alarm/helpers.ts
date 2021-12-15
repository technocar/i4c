import { Labels } from "../services/models/constants";

export interface AlarmPeriod {
  value: number,
  type: string,
  display: string
}

export class AlarmHelpers {

  private static getPeriodInterval(code: string): number {
    switch (code) {
      case "Y":
        return 60*60*24*365;
      case "M":
        return 60*60*24*31;
      case "D":
        return 60*60*24;
      case "H":
        return 60*60;
      case "m":
        return 60;
      default:
        return 1;
    }
  }

  public static getPeriod(seconds: number): AlarmPeriod {
    var p: AlarmPeriod = undefined;
    if ((seconds ?? undefined) === undefined)
      return p;

    Labels.periods.slice(0).reverse().forEach((period) => {
      var interval: number = this.getPeriodInterval(period[0]);
      var value = 0;
      value = seconds / interval;
      if (value > 0) {
        p = {
          display: `${value.toFixed(0)}${period[2]}`,
          type: period[0],
          value: value
        }
        return;
      }
    });
    return p;
  }

  public static getMaxFreqValue(period: AlarmPeriod): number {
    if (!period)
      return 0;

    var interval: number = this.getPeriodInterval(period.type);
    return period.value * interval;
  }
}
