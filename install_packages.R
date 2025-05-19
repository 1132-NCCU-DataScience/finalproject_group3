#!/usr/bin/env Rscript

# 檢查並安裝所需的套件
required_packages <- c(
    "shiny",
    "shinydashboard",
    "leaflet",
    "dplyr",
    "plotly",
    "lubridate",
    "DT",
    "future",
    "promises",
    "jsonlite",
    "reticulate"
)

# 安裝缺少的套件
new_packages <- required_packages[!(required_packages %in% installed.packages()[,"Package"])]
if(length(new_packages)) {
    install.packages(new_packages, repos = "https://cloud.r-project.org")
}

# 載入套件並檢查版本
for(pkg in required_packages) {
    library(pkg, character.only = TRUE)
    cat(sprintf("%s version: %s\n", pkg, packageVersion(pkg)))
} 