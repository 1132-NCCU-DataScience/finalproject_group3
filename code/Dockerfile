# Starlink 台北衛星分析系統 - Shiny Docker 容器
FROM ubuntu:22.04

# 設置環境變數
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Asia/Taipei

# 設置工作目錄
WORKDIR /app

# 安裝系統依賴
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    r-base \
    r-base-dev \
    curl \
    wget \
    ca-certificates \
    tzdata \
    locales \
    && rm -rf /var/lib/apt/lists/*

# 設置時區和語言環境
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone
RUN locale-gen zh_TW.UTF-8
ENV LANG=zh_TW.UTF-8
ENV LANGUAGE=zh_TW:zh
ENV LC_ALL=zh_TW.UTF-8

# 複製 requirements 文件
COPY requirements/base.txt /app/requirements/base.txt
COPY environment.yml /app/environment.yml

# 安裝 Python 依賴
RUN pip3 install --no-cache-dir -r requirements/base.txt

# 安裝 R 套件
RUN R -e "install.packages(c('shiny', 'shinydashboard', 'plotly', 'DT', 'ggplot2', 'dplyr', 'scales', 'jsonlite', 'reticulate'), repos='https://cran.rstudio.com/')"

# 複製應用程式文件
COPY . /app

# 建立輸出目錄
RUN mkdir -p /app/output

# 設置權限
RUN chown -R nobody:nogroup /app
USER nobody

# 暴露 Shiny 應用端口
EXPOSE 3838

# 健康檢查
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:3838/ || exit 1

# 啟動 Shiny 應用
CMD ["python3", "starlink.py", "shiny", "--host", "0.0.0.0", "--port", "3838"] 