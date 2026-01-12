"""
Superset Configuration for E-commerce Price Comparison Dashboard
"""

import os

# Database Configuration
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://ecommerce_user:ecommerce_password@localhost:5432/ecommerce_price_comparison')

# Redis Configuration
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

# Secret Key
SECRET_KEY = os.getenv('SUPERSET_SECRET_KEY', '1871742e3b671a4f0e35b97071c4ad7d990aa532558d324d1765a84b0ae3ab60')

# Security Configuration
ENABLE_PROXY_FIX = True
ENABLE_CORS = True
CORS_OPTIONS = {
    'origins': ['*'],
    'methods': ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
    'allow_headers': ['Content-Type', 'Authorization']
}

# Feature Flags
FEATURE_FLAGS = {
    'ALERT_REPORTS': True,
    'DASHBOARD_RBAC': True,
    'DASHBOARD_NATIVE_FILTERS': True,
    'ENABLE_TEMPLATE_PROCESSING': True,
    'GENERIC_CHART_AXES_FORMATTING': True,
    'DASHBOARD_CROSS_FILTERS': True,
    'DASHBOARD_FILTER_BAR': True,
    'DASHBOARD_POSITIONING': True,
    'GLOBAL_ASYNC_QUERIES': True,
}

# Email Configuration (optional)
EMAIL_NOTIFICATIONS = False
SMTP_HOST = os.getenv('SMTP_HOST', 'localhost')
SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
SMTP_USER = os.getenv('SMTP_USER', '')
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD', '')
SMTP_MAIL_FROM = os.getenv('SMTP_MAIL_FROM', 'noreply@ecommerce.com')

# Timezone
TIMEZONE = 'Africa/Nairobi'

# Logging
LOG_LEVEL = 'INFO'
LOG_FORMAT = '%(asctime)s:%(name)s:%(levelname)s:%(message)s'

# Upload Settings
UPLOAD_FOLDER = '/app/uploads'
MAX_UPLOAD_SIZE = 100 * 1024 * 1024  # 100MB

# Cache Configuration
CACHE_CONFIG = {
    'CACHE_TYPE': 'redis',
    'CACHE_REDIS_URL': REDIS_URL,
    'CACHE_DEFAULT_TIMEOUT': 300
}

# Webserver Configuration
WEBDRIVER_TYPE = 'chrome'
WEBDRIVER_BASEURL = 'http://chrome:4444/wd/hub'

# SQL Lab
SQLLAB_TIMEOUT = 3600
SQLLAB_MAX_ROWS = 10000
SQLLAB_TIMEOUT_READ_ONLY = 300

# Dashboard Configuration
DEFAULT_TIMEZONE = 'Africa/Nairobi'
ENABLE_TIMEZONE_CONVERSION = True

# Security
TALISMAN_ENABLED = False
WTF_CSRF_ENABLED = True
WTF_CSRF_TIME_LIMIT = 60 * 60 * 24 * 30  # 30 days

# Performance
ENABLE_CHUNK_ENCODING = True
ENABLE_JAVASCRIPT_DEBUGGING = False

# API Configuration
ENABLE_API_JSON_LOG = True
API_JSON_LOG_PAYLOAD = True

# Database connection settings
SQLALCHEMY_TRACK_MODIFICATIONS = False
SQLALCHEMY_ENGINE_OPTIONS = {
    'pool_size': 10,
    'pool_recycle': 3600,
    'pool_pre_ping': True,
    'max_overflow': 20
}

# Custom CSS for dashboard
CUSTOM_SECURITY_MANAGER = None

# Chart settings
DEFAULT_VEGA_THEME = "light"

# Export settings
CSV_EXPORT = True
EXCEL_EXPORT = True
