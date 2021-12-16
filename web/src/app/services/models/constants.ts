import { StatVisualSettingsLegendAlign, StatVisualSettingsLegendPosition } from "./api";

export enum DeviceType { Mill = "mill", Lathe = "lathe", GOM = "gom", Robot = "robot" }

export class Labels {

  static analysis = {
    legend: {
      positions: [
        [StatVisualSettingsLegendPosition.Top, $localize `:@@analysis_legend_position_top:Fent`],
        [StatVisualSettingsLegendPosition.Bottom, $localize `:@@analysis_legend_position_bottom:Lent`],
        [StatVisualSettingsLegendPosition.Left, $localize `:@@analysis_legend_position_left:Baloldal`],
        [StatVisualSettingsLegendPosition.Right, $localize `:@@analysis_legend_position_right:Jobboldal`]
      ],
      aligns: [
        [StatVisualSettingsLegendAlign.Start, $localize `:@@analysis_legend_align_start:Elől`],
        [StatVisualSettingsLegendAlign.End, $localize `:@@analysis_legend_align_end:Hátul`],
        [StatVisualSettingsLegendAlign.Center, $localize `:@@analysis_legend_align_center:Középen`]
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
}
