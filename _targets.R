library(targets)
library(targets)
library(tidyverse)
library(reticulate)
library(sf)
library(leaflet)
use_condaenv("starlink-env", required = TRUE)
py_run_string("from skyfield.api import load, wgs84")
list(tar_target(tle_url, "https://celestrak.org/NORAD/elements/gp.php?GROUP=starlink&FORMAT=tle", 
    format = "url"), tar_target(tle_raw, readLines(tle_url)), 
    tar_target(gs_url, "https://satellitemap.space/data/ground_stations.json", 
        format = "url"), tar_target(gs_json, jsonlite::fromJSON(gs_url, 
        simplifyVector = TRUE)), tar_target(taipei_coords, list(lat = 25.033, 
        lon = 121.5654, elevation = 10)), tar_target(visibility_py, 
        source_python("py/visibility.py")), tar_target(visible_data, 
        compute_visibility(tle_raw, taipei_coords$lat, taipei_coords$lon, 
            taipei_coords$elevation, interval_minutes = 1, duration_hours = 24)), 
    tar_target(handover_data, source_file("R/compute_handover.R")(visible_data)), 
    tar_target(fig_timeline, source_file("R/plot_timeline.R")(visible_data, 
        handover_data)), tar_target(fig_heatmap, source_file("R/plot_heatmap.R")(visible_data)), 
    tar_target(report_data, list(visible_data = visible_data, 
        handover_data = handover_data, fig_timeline = fig_timeline, 
        fig_heatmap = fig_heatmap)), tar_target(report, rmarkdown::render("Rmd/report.qmd", 
        params = list(data = report_data), output_file = "../output/starlink_analysis_report.html")))
