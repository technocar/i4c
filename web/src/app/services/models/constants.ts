import { AlarmNotificationType, StatVisualSettingsChartLegendAlign, StatVisualSettingsChartLegendPosition } from "./api";

export enum DeviceType { Mill = "mill", Lathe = "lathe", GOM = "gom", Robot = "robot" }

export class Labels {

  static analysis = {
    legend: {
      positions: [
        [StatVisualSettingsChartLegendPosition.Top, $localize `:@@analysis_legend_position_top:Fent`],
        [StatVisualSettingsChartLegendPosition.Bottom, $localize `:@@analysis_legend_position_bottom:Lent`],
        [StatVisualSettingsChartLegendPosition.Left, $localize `:@@analysis_legend_position_left:Baloldal`],
        [StatVisualSettingsChartLegendPosition.Right, $localize `:@@analysis_legend_position_right:Jobboldal`]
      ],
      aligns: [
        [StatVisualSettingsChartLegendAlign.Start, $localize `:@@analysis_legend_align_start:Elől`],
        [StatVisualSettingsChartLegendAlign.End, $localize `:@@analysis_legend_align_end:Hátul`],
        [StatVisualSettingsChartLegendAlign.Center, $localize `:@@analysis_legend_align_center:Középen`]
      ]
    }
  }

  static periods = [
    ['s', $localize `:@@datetime_second:másodperc`, $localize `:@@datetime_second_short:mp`],
    ['m', $localize `:@@datetime_minute:perc`, $localize `:@@datetime_minute_short:p`],
    ['H', $localize `:@@datetime_hour:óra`, $localize `:@@datetime_hour_short:óra`],
    ['D', $localize `:@@datetime_day:nap`, $localize `:@@datetime_day_short:nap`],
    ['M', $localize `:@@datetime_month:hónap`, $localize `:@@datetime_month_short:hónap`],
    ['Y', $localize `:@@datetime_year:év`, $localize `:@@datetime_year_short:év`]
  ]

  static alarm = {
    methods: [
      [AlarmNotificationType.None, $localize `:@@alarm_method_none:Nincs`],
      [AlarmNotificationType.Email, $localize `:@@alarm_method_email:E-mail`],
      [AlarmNotificationType.Push, $localize `:@@alarm_method_push:Push`],
      [AlarmNotificationType.Telegram, $localize `:@@alarm_method_telegram:Telegram`]
    ]
  }
}
