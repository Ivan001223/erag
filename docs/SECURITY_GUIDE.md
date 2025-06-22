# 安全配置指南

## 概述

本文档描述了智能知识库系统的安全配置和最佳实践，包括认证、授权、数据保护、网络安全等方面。

## 认证和授权

### JWT配置

#### 基础配置
```bash
# JWT密钥配置
JWT_SECRET_KEY=your-super-secret-key-at-least-32-characters
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30
JWT_REFRESH_TOKEN_EXPIRE_DAYS=7

# 令牌发行者和受众
JWT_ISSUER=knowledge-system
JWT_AUDIENCE=knowledge-system-api
```

#### 高级配置
```python
# backend/config/security.py
JWT_CONFIG = {
    "secret_key": os.getenv("JWT_SECRET_KEY"),
    "algorithm": "HS256",
    "access_token_expire_minutes": 30,
    "refresh_token_expire_days": 7,
    "issuer": "knowledge-system",
    "audience": "knowledge-system-api",
    "leeway": 10,  # 时钟偏移容忍度（秒）
    "verify_signature": True,
    "verify_exp": True,
    "verify_nbf": True,
    "verify_iat": True,
    "require_exp": True,
    "require_iat": True,
}
```

### 权限系统

#### 角色定义
```python
ROLES = {
    "super_admin": {
        "permissions": ["*"],
        "description": "超级管理员，拥有所有权限"
    },
    "admin": {
        "permissions": [
            "entity:*", "relation:*", "document:*",
            "user:read", "user:write", "system:read",
            "backup:read", "backup:write"
        ],
        "description": "管理员，拥有业务管理权限"
    },
    "editor": {
        "permissions": [
            "entity:read", "entity:write",
            "relation:read", "relation:write",
            "document:read", "document:write",
            "search:read"
        ],
        "description": "编辑者，可以编辑知识内容"
    },
    "viewer": {
        "permissions": [
            "entity:read", "relation:read",
            "document:read", "search:read"
        ],
        "description": "查看者，只能查看内容"
    }
}
```

#### 资源权限
```python
PERMISSIONS = {
    # 实体权限
    "entity:read": "查看实体",
    "entity:write": "编辑实体",
    "entity:delete": "删除实体",
    
    # 关系权限
    "relation:read": "查看关系",
    "relation:write": "编辑关系",
    "relation:delete": "删除关系",
    
    # 文档权限
    "document:read": "查看文档",
    "document:write": "编辑文档",
    "document:delete": "删除文档",
    "document:upload": "上传文档",
    
    # 搜索权限
    "search:read": "执行搜索",
    "search:advanced": "高级搜索",
    
    # 用户管理权限
    "user:read": "查看用户",
    "user:write": "编辑用户",
    "user:delete": "删除用户",
    
    # 系统管理权限
    "system:read": "查看系统信息",
    "system:write": "修改系统配置",
    "backup:read": "查看备份",
    "backup:write": "执行备份和恢复",
}
```

## API安全

### 限流配置

#### 基础限流
```python
# 默认限流规则
DEFAULT_RATE_LIMITS = {
    "requests_per_minute": 60,
    "requests_per_hour": 1000,
    "requests_per_day": 10000,
    "burst_limit": 10,
}

# 角色特定限流
ROLE_RATE_LIMITS = {
    "viewer": {
        "requests_per_minute": 30,
        "requests_per_hour": 500,
        "requests_per_day": 5000,
    },
    "editor": {
        "requests_per_minute": 100,
        "requests_per_hour": 2000,
        "requests_per_day": 20000,
    },
    "admin": {
        "requests_per_minute": 300,
        "requests_per_hour": 5000,
        "requests_per_day": 50000,
    },
    "super_admin": {
        "requests_per_minute": 1000,
        "requests_per_hour": 20000,
        "requests_per_day": 200000,
    }
}
```

#### 端点特定限流
```python
ENDPOINT_RATE_LIMITS = {
    "/auth/login": {
        "requests_per_minute": 5,
        "requests_per_hour": 20,
    },
    "/api/v1/documents": {
        "requests_per_minute": 10,  # 文档上传限制
        "requests_per_hour": 100,
    },
    "/api/v1/search": {
        "requests_per_minute": 30,
        "requests_per_hour": 500,
    },
}
```

### IP访问控制

#### 白名单配置
```bash
# 允许访问的IP范围
IP_WHITELIST=192.168.1.0/24,10.0.0.0/8,172.16.0.0/12

# 管理员IP限制
ADMIN_IP_WHITELIST=192.168.1.100,192.168.1.101

# API访问IP限制
API_IP_WHITELIST=0.0.0.0/0  # 生产环境应限制
```

#### 黑名单配置
```bash
# 禁止访问的IP
IP_BLACKLIST=192.168.1.200,10.0.0.100

# 自动黑名单（基于异常行为）
AUTO_BLACKLIST_ENABLED=true
AUTO_BLACKLIST_THRESHOLD=100  # 每分钟请求数阈值
AUTO_BLACKLIST_DURATION=3600  # 黑名单持续时间（秒）
```

### 安全头配置

```python
SECURITY_HEADERS = {
    # 内容安全策略
    "Content-Security-Policy": (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data: https:; "
        "font-src 'self' data:; "
        "connect-src 'self' wss: https:; "
        "frame-ancestors 'none';"
    ),
    
    # 严格传输安全
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    
    # 内容类型嗅探保护
    "X-Content-Type-Options": "nosniff",
    
    # 点击劫持保护
    "X-Frame-Options": "DENY",
    
    # XSS保护
    "X-XSS-Protection": "1; mode=block",
    
    # 引用者策略
    "Referrer-Policy": "strict-origin-when-cross-origin",
    
    # 权限策略
    "Permissions-Policy": (
        "camera=(), microphone=(), geolocation=(), "
        "payment=(), usb=(), magnetometer=(), gyroscope=()"
    ),
}
```

## 数据保护

### 数据库安全

#### PostgreSQL配置
```bash
# 数据库连接安全
DATABASE_URL=postgresql://username:password@localhost:5432/knowledge_db?sslmode=require

# 连接池配置
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=30
DB_POOL_TIMEOUT=30
DB_POOL_RECYCLE=3600

# SSL配置
DB_SSL_CERT_PATH=/path/to/client-cert.pem
DB_SSL_KEY_PATH=/path/to/client-key.pem
DB_SSL_CA_PATH=/path/to/ca-cert.pem
```

#### Neo4j安全配置
```bash
# Neo4j认证
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-secure-password

# 加密连接
NEO4J_ENCRYPTED=true
NEO4J_TRUST=TRUST_ALL_CERTIFICATES

# 连接池
NEO4J_MAX_CONNECTION_LIFETIME=3600
NEO4J_MAX_CONNECTION_POOL_SIZE=50
NEO4J_CONNECTION_ACQUISITION_TIMEOUT=60
```

#### Redis安全配置
```bash
# Redis认证
REDIS_URL=redis://:password@localhost:6379/0

# SSL/TLS
REDIS_SSL=true
REDIS_SSL_CERT_REQS=required
REDIS_SSL_CA_CERTS=/path/to/ca.crt
REDIS_SSL_CERTFILE=/path/to/client.crt
REDIS_SSL_KEYFILE=/path/to/client.key
```

### 数据加密

#### 传输加密
```nginx
# Nginx SSL配置
server {
    listen 443 ssl http2;
    server_name api.knowledge-system.com;
    
    ssl_certificate /etc/ssl/certs/api.knowledge-system.com.crt;
    ssl_certificate_key /etc/ssl/private/api.knowledge-system.com.key;
    
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    
    ssl_session_timeout 10m;
    ssl_session_cache shared:SSL:10m;
    ssl_session_tickets off;
    
    ssl_stapling on;
    ssl_stapling_verify on;
    
    add_header Strict-Transport-Security "max-age=63072000" always;
}
```

#### 存储加密
```python
# 敏感数据加密配置
ENCRYPTION_CONFIG = {
    "algorithm": "AES-256-GCM",
    "key_derivation": "PBKDF2",
    "key_iterations": 100000,
    "key_length": 32,
    "salt_length": 16,
}

# 文件存储加密
FILE_ENCRYPTION_ENABLED = True
FILE_ENCRYPTION_KEY = os.getenv("FILE_ENCRYPTION_KEY")

# 数据库字段加密
DB_FIELD_ENCRYPTION_ENABLED = True
DB_ENCRYPTION_KEY = os.getenv("DB_ENCRYPTION_KEY")
```

## 网络安全

### 防火墙配置

#### UFW配置（Ubuntu）
```bash
# 基础防火墙规则
sudo ufw default deny incoming
sudo ufw default allow outgoing

# 允许SSH
sudo ufw allow ssh

# 允许HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# 允许应用端口（仅内网）
sudo ufw allow from 192.168.1.0/24 to any port 8000
sudo ufw allow from 192.168.1.0/24 to any port 7474
sudo ufw allow from 192.168.1.0/24 to any port 6379

# 启用防火墙
sudo ufw enable
```

#### iptables配置
```bash
#!/bin/bash
# 基础iptables规则

# 清空现有规则
iptables -F
iptables -X
iptables -t nat -F
iptables -t nat -X

# 默认策略
iptables -P INPUT DROP
iptables -P FORWARD DROP
iptables -P OUTPUT ACCEPT

# 允许本地回环
iptables -A INPUT -i lo -j ACCEPT

# 允许已建立的连接
iptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT

# 允许SSH
iptables -A INPUT -p tcp --dport 22 -j ACCEPT

# 允许HTTP/HTTPS
iptables -A INPUT -p tcp --dport 80 -j ACCEPT
iptables -A INPUT -p tcp --dport 443 -j ACCEPT

# 允许内网访问应用端口
iptables -A INPUT -s 192.168.1.0/24 -p tcp --dport 8000 -j ACCEPT

# DDoS防护
iptables -A INPUT -p tcp --dport 80 -m limit --limit 25/minute --limit-burst 100 -j ACCEPT
iptables -A INPUT -p tcp --dport 443 -m limit --limit 25/minute --limit-burst 100 -j ACCEPT
```

### DDoS防护

#### Nginx限制配置
```nginx
# 限制请求频率
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
limit_req_zone $binary_remote_addr zone=login:10m rate=1r/s;

# 限制连接数
limit_conn_zone $binary_remote_addr zone=conn_limit_per_ip:10m;

server {
    # 应用限制
    limit_req zone=api burst=20 nodelay;
    limit_conn conn_limit_per_ip 10;
    
    # 登录接口特殊限制
    location /auth/login {
        limit_req zone=login burst=5 nodelay;
    }
    
    # 缓冲区大小限制
    client_body_buffer_size 1K;
    client_header_buffer_size 1k;
    client_max_body_size 100M;
    large_client_header_buffers 2 1k;
}
```

#### Fail2Ban配置
```ini
# /etc/fail2ban/jail.local
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5

[nginx-http-auth]
enabled = true
filter = nginx-http-auth
logpath = /var/log/nginx/error.log
maxretry = 3

[nginx-limit-req]
enabled = true
filter = nginx-limit-req
logpath = /var/log/nginx/error.log
maxretry = 10

[nginx-dos]
enabled = true
filter = nginx-dos
logpath = /var/log/nginx/access.log
maxretry = 300
findtime = 300
bantime = 600
```

## 监控和审计

### 安全日志配置

```python
# 安全事件日志配置
SECURITY_LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "security": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S"
        }
    },
    "handlers": {
        "security_file": {
            "level": "INFO",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "/var/log/knowledge-system/security.log",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 10,
            "formatter": "security"
        },
        "security_syslog": {
            "level": "WARNING",
            "class": "logging.handlers.SysLogHandler",
            "address": ("localhost", 514),
            "formatter": "security"
        }
    },
    "loggers": {
        "security": {
            "handlers": ["security_file", "security_syslog"],
            "level": "INFO",
            "propagate": False
        }
    }
}
```

### 安全事件监控

```python
# 需要监控的安全事件
SECURITY_EVENTS = {
    "AUTH_SUCCESS": "用户登录成功",
    "AUTH_FAILURE": "用户登录失败",
    "AUTH_LOGOUT": "用户注销",
    "TOKEN_REFRESH": "令牌刷新",
    "TOKEN_REVOKE": "令牌撤销",
    "PERMISSION_DENIED": "权限拒绝",
    "RATE_LIMIT_EXCEEDED": "请求频率超限",
    "IP_BLOCKED": "IP地址被阻止",
    "SUSPICIOUS_ACTIVITY": "可疑活动",
    "DATA_ACCESS": "敏感数据访问",
    "DATA_MODIFICATION": "数据修改",
    "ADMIN_ACTION": "管理员操作",
    "SECURITY_VIOLATION": "安全违规",
}
```

### 告警规则

```yaml
# Prometheus告警规则
groups:
  - name: security
    rules:
      - alert: HighFailedLoginRate
        expr: rate(auth_failures_total[5m]) > 0.1
        for: 2m
        annotations:
          summary: "登录失败率过高"
          description: "过去5分钟登录失败率超过10%"

      - alert: SuspiciousIPActivity
        expr: rate(http_requests_total{status=~"4.."}[5m]) by (client_ip) > 1
        for: 1m
        annotations:
          summary: "可疑IP活动"
          description: "IP {{ $labels.client_ip }} 产生大量4XX错误"

      - alert: UnauthorizedAccess
        expr: increase(permission_denied_total[5m]) > 10
        for: 1m
        annotations:
          summary: "未授权访问尝试"
          description: "过去5分钟权限拒绝次数超过10次"

      - alert: RateLimitExceeded
        expr: increase(rate_limit_exceeded_total[5m]) > 50
        for: 2m
        annotations:
          summary: "请求频率限制触发"
          description: "过去5分钟频率限制触发超过50次"
```

## 安全最佳实践

### 开发安全

1. **代码安全**
   - 使用静态代码分析工具（Bandit、SonarQube）
   - 定期更新依赖包，修复安全漏洞
   - 避免硬编码敏感信息
   - 实施代码审查流程

2. **输入验证**
   - 严格验证所有用户输入
   - 使用参数化查询防止SQL注入
   - 实施XSS防护措施
   - 限制文件上传类型和大小

3. **错误处理**
   - 不在错误信息中泄露敏感信息
   - 实施统一的错误处理机制
   - 记录详细的错误日志
   - 为用户提供友好的错误提示

### 运维安全

1. **系统加固**
   - 定期更新操作系统和软件包
   - 禁用不必要的服务和端口
   - 配置强密码策略
   - 实施最小权限原则

2. **备份安全**
   - 加密备份数据
   - 定期测试备份恢复
   - 异地存储备份文件
   - 限制备份访问权限

3. **网络安全**
   - 使用VPN进行远程访问
   - 实施网络分段
   - 配置入侵检测系统
   - 定期进行安全扫描

### 合规要求

1. **数据保护法规**
   - GDPR（欧盟通用数据保护条例）
   - CCPA（加州消费者隐私法案）
   - 网络安全法（中国）
   - 数据安全法（中国）

2. **行业标准**
   - ISO 27001（信息安全管理）
   - SOC 2（服务组织控制）
   - PCI DSS（支付卡行业数据安全标准）
   - NIST网络安全框架

3. **合规检查清单**
   - [ ] 数据分类和标记
   - [ ] 访问控制和权限管理
   - [ ] 数据加密和保护
   - [ ] 审计日志和监控
   - [ ] 事件响应计划
   - [ ] 定期安全评估
   - [ ] 员工安全培训
   - [ ] 第三方安全评估

## 安全事件响应

### 事件分类

```python
SECURITY_INCIDENT_LEVELS = {
    "LOW": {
        "description": "轻微安全事件",
        "response_time": "24小时",
        "examples": ["单次登录失败", "轻微配置错误"]
    },
    "MEDIUM": {
        "description": "中等安全事件", 
        "response_time": "4小时",
        "examples": ["多次登录失败", "权限提升尝试"]
    },
    "HIGH": {
        "description": "严重安全事件",
        "response_time": "1小时", 
        "examples": ["数据泄露", "系统入侵"]
    },
    "CRITICAL": {
        "description": "紧急安全事件",
        "response_time": "15分钟",
        "examples": ["大规模数据泄露", "系统完全妥协"]
    }
}
```

### 响应流程

1. **检测和分析**
   - 自动检测安全事件
   - 分析事件严重程度
   - 确定影响范围
   - 收集相关证据

2. **遏制和恢复**
   - 隔离受影响系统
   - 阻止进一步损害
   - 恢复正常服务
   - 修复安全漏洞

3. **后续处理**
   - 事件报告和文档
   - 根因分析
   - 改进安全措施
   - 经验教训总结

### 联系信息

```bash
# 安全团队联系方式
SECURITY_TEAM_EMAIL=security@company.com
SECURITY_TEAM_PHONE=+86-xxx-xxxx-xxxx
SECURITY_INCIDENT_HOTLINE=+86-xxx-xxxx-xxxx

# 紧急联系人
SECURITY_MANAGER=manager@company.com
COMPLIANCE_OFFICER=compliance@company.com
LEGAL_COUNSEL=legal@company.com
``` 