"""
项目交付打包器

在流水线最后阶段收敛产物，输出交付清单、报告和压缩包。
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


@dataclass(frozen=True)
class ArtifactSpec:
    """交付物规则定义"""

    path: Path
    required: bool
    reason: str


class DeliveryPackager:
    """交付包生成器"""

    def __init__(self, project_dir: Path, name: str, version: str = "2.4.0"):
        self.project_dir = Path(project_dir).resolve()
        self.name = name
        self.version = version

    def package(self, cicd_platform: str = "all") -> dict[str, object]:
        """生成交付清单、报告和压缩包"""
        output_dir = self.project_dir / "output" / "delivery"
        output_dir.mkdir(parents=True, exist_ok=True)

        specs = self._artifact_specs(cicd_platform=cicd_platform)
        included_files: list[str] = []
        missing_required: list[dict[str, str]] = []

        for spec in specs:
            if spec.path.exists():
                included_files.append(self._relative(spec.path))
            elif spec.required:
                missing_required.append(
                    {
                        "path": self._relative(spec.path),
                        "reason": spec.reason,
                    }
                )

        migration_files = self._collect_migration_files()
        if migration_files:
            included_files.extend(self._relative(path) for path in migration_files)
        else:
            missing_required.append(
                {
                    "path": "migrations/*",
                    "reason": "缺少数据库迁移脚本（至少应生成一种 ORM 迁移文件）",
                }
            )

        spec_task_summary = self._collect_spec_task_summary()
        if int(spec_task_summary["task_files"]) > 0:
            if int(spec_task_summary["pending"]) > 0:
                target_change = str(spec_task_summary.get("target_change", "")).strip()
                target_path = ".super-dev/changes/*/tasks.md"
                if target_change:
                    target_path = f".super-dev/changes/{target_change}/tasks.md"
                missing_required.append(
                    {
                        "path": target_path,
                        "reason": f"存在未完成 Spec 任务: {spec_task_summary['pending']}",
                    }
                )

        included_files = sorted(set(included_files))
        status = "ready" if not missing_required else "incomplete"

        manifest: dict[str, object] = {
            "project_name": self.name,
            "version": self.version,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "status": status,
            "cicd_platform": cicd_platform,
            "included_files": included_files,
            "missing_required": missing_required,
            "spec_tasks": spec_task_summary,
            "summary": {
                "included_count": len(included_files),
                "missing_required_count": len(missing_required),
            },
        }

        manifest_file = output_dir / f"{self.name}-delivery-manifest.json"
        manifest_file.write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        report_file = output_dir / f"{self.name}-delivery-report.md"
        report_file.write_text(self._to_markdown(manifest), encoding="utf-8")

        archive_file = output_dir / f"{self.name}-delivery-v{self.version}.zip"
        self._build_archive(
            archive_path=archive_file,
            included_files=included_files,
            extra_files=[manifest_file, report_file],
        )

        return {
            "status": status,
            "manifest_file": str(manifest_file),
            "report_file": str(report_file),
            "archive_file": str(archive_file),
            "included_count": len(included_files),
            "missing_required_count": len(missing_required),
            "missing_required": missing_required,
        }

    def _artifact_specs(self, cicd_platform: str) -> list[ArtifactSpec]:
        output_dir = self.project_dir / "output"
        specs = [
            ArtifactSpec(output_dir / f"{self.name}-research.md", True, "缺少需求增强报告"),
            ArtifactSpec(output_dir / f"{self.name}-prd.md", True, "缺少 PRD"),
            ArtifactSpec(output_dir / f"{self.name}-architecture.md", True, "缺少架构文档"),
            ArtifactSpec(output_dir / f"{self.name}-uiux.md", True, "缺少 UI/UX 文档"),
            ArtifactSpec(output_dir / f"{self.name}-ui-contract.json", True, "缺少 UI 系统契约"),
            ArtifactSpec(output_dir / f"{self.name}-execution-plan.md", True, "缺少执行路线图"),
            ArtifactSpec(output_dir / f"{self.name}-frontend-blueprint.md", True, "缺少前端蓝图"),
            ArtifactSpec(output_dir / f"{self.name}-redteam.md", True, "缺少红队报告"),
            ArtifactSpec(output_dir / f"{self.name}-quality-gate.md", True, "缺少质量门禁报告"),
            ArtifactSpec(output_dir / f"{self.name}-code-review.md", True, "缺少代码审查指南"),
            ArtifactSpec(output_dir / f"{self.name}-ai-prompt.md", True, "缺少 AI 提示词"),
            ArtifactSpec(
                output_dir / f"{self.name}-task-execution.md", True, "缺少 Spec 任务执行报告"
            ),
            ArtifactSpec(
                output_dir / f"{self.name}-frontend-runtime.md", True, "缺少前端运行验证报告"
            ),
            ArtifactSpec(
                output_dir / f"{self.name}-frontend-runtime.json", True, "缺少前端运行验证数据"
            ),
            ArtifactSpec(self.project_dir / "preview.html", True, "缺少前端预览页"),
            ArtifactSpec(output_dir / "frontend" / "index.html", True, "缺少前端演示页面"),
            ArtifactSpec(output_dir / "frontend" / "styles.css", True, "缺少前端演示样式"),
            ArtifactSpec(
                output_dir / "frontend" / "design-tokens.css", True, "缺少前端 Design Token 样式"
            ),
            ArtifactSpec(output_dir / "frontend" / "app.js", True, "缺少前端演示脚本"),
            ArtifactSpec(self.project_dir / "backend" / "API_CONTRACT.md", True, "缺少 API 契约"),
            ArtifactSpec(self.project_dir / ".env.deploy.example", True, "缺少部署环境模板"),
            ArtifactSpec(
                self.project_dir / "output" / "deploy" / "all-secrets-checklist.md",
                True,
                "缺少部署 Secrets 检查清单",
            ),
        ]
        specs.extend(self._cicd_specs(cicd_platform=cicd_platform))
        return specs

    def _cicd_specs(self, cicd_platform: str) -> list[ArtifactSpec]:
        mapping: dict[str, list[str]] = {
            "github": [".github/workflows/ci.yml", ".github/workflows/cd.yml"],
            "gitlab": [".gitlab-ci.yml"],
            "jenkins": ["Jenkinsfile"],
            "azure": [".azure-pipelines.yml"],
            "bitbucket": ["bitbucket-pipelines.yml"],
            "all": [
                ".github/workflows/ci.yml",
                ".github/workflows/cd.yml",
                ".gitlab-ci.yml",
                "Jenkinsfile",
                ".azure-pipelines.yml",
                "bitbucket-pipelines.yml",
            ],
        }
        files = mapping.get(cicd_platform, mapping["github"])
        return [
            ArtifactSpec(self.project_dir / relative, True, f"缺少 CI/CD 文件: {relative}")
            for relative in files
        ]

    def _collect_migration_files(self) -> list[Path]:
        patterns = [
            "prisma/migrations/**/*.sql",
            "alembic/versions/*.py",
            "backend/migrations/**/*.sql",
            "backend/migrations/**/*.py",
            "migrations/**/*.sql",
            "src/main/resources/db/migration/*.sql",
        ]
        files: list[Path] = []
        for pattern in patterns:
            files.extend(self.project_dir.glob(pattern))
        return sorted(path for path in files if path.is_file())

    def _build_archive(
        self,
        archive_path: Path,
        included_files: list[str],
        extra_files: list[Path],
    ) -> None:
        with ZipFile(archive_path, mode="w", compression=ZIP_DEFLATED) as archive:
            for relative in included_files:
                file_path = self.project_dir / relative
                if file_path.exists():
                    archive.write(file_path, arcname=relative)
            for file_path in extra_files:
                if file_path.exists():
                    arcname = self._relative(file_path)
                    archive.write(file_path, arcname=arcname)

    def _to_markdown(self, manifest: dict[str, object]) -> str:
        status = str(manifest.get("status", "incomplete"))
        status_text = "可交付" if status == "ready" else "未完成"
        included = manifest.get("included_files", [])
        missing = manifest.get("missing_required", [])
        cicd_platform = manifest.get("cicd_platform", "all")

        lines = [
            "# 交付报告",
            "",
            f"- 项目: {manifest.get('project_name', self.name)}",
            f"- 版本: {manifest.get('version', self.version)}",
            f"- 状态: {status_text} ({status})",
            f"- CI/CD 平台: {cicd_platform}",
            f"- 生成时间: {manifest.get('generated_at', '')}",
            "",
            "## 已包含文件",
            "",
        ]

        if isinstance(included, list) and included:
            for item in included:
                lines.append(f"- {item}")
        else:
            lines.append("- (none)")
        lines.append("")

        lines.extend(["## 缺失必需项", ""])
        if isinstance(missing, list) and missing:
            for item in missing:
                if isinstance(item, dict):
                    lines.append(f"- {item.get('path', 'unknown')}: {item.get('reason', '')}")
        else:
            lines.append("- 无")
        lines.append("")

        spec_tasks = manifest.get("spec_tasks", {})
        if isinstance(spec_tasks, dict):
            lines.extend(
                [
                    "## Spec任务摘要",
                    "",
                    f"- tasks.md 文件数: {spec_tasks.get('task_files', 0)}",
                    f"- 总任务数: {spec_tasks.get('total', 0)}",
                    f"- 已完成: {spec_tasks.get('completed', 0)}",
                    f"- 进行中/未完成: {spec_tasks.get('pending', 0)}",
                    "",
                ]
            )
        return "\n".join(lines)

    def _relative(self, path: Path) -> str:
        try:
            return str(path.relative_to(self.project_dir))
        except ValueError:
            return str(path)

    # ------------------------------------------------------------------
    # Kubernetes 部署配置生成
    # ------------------------------------------------------------------

    def generate_kubernetes_configs(
        self,
        image: str = "",
        replicas: int = 2,
        port: int = 3000,
        cpu_limit: str = "500m",
        memory_limit: str = "512Mi",
        domain: str = "",
    ) -> dict[str, str]:
        """生成 Kubernetes 部署配置（Deployment/Service/Ingress/HPA）。

        返回文件名 -> 内容的映射。
        """
        image = image or f"{self.name}:v{self.version}"
        domain = domain or f"{self.name}.example.com"
        app_label = re.sub(r"[^a-z0-9-]", "-", self.name.lower())[:63]

        configs: dict[str, str] = {}

        # --- Deployment ---
        configs[
            "deployment.yaml"
        ] = f"""apiVersion: apps/v1
kind: Deployment
metadata:
  name: {app_label}
  labels:
    app: {app_label}
    version: "{self.version}"
spec:
  replicas: {replicas}
  selector:
    matchLabels:
      app: {app_label}
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 0
      maxSurge: 1
  template:
    metadata:
      labels:
        app: {app_label}
        version: "{self.version}"
    spec:
      terminationGracePeriodSeconds: 30
      containers:
        - name: {app_label}
          image: {image}
          imagePullPolicy: IfNotPresent
          ports:
            - containerPort: {port}
              protocol: TCP
          envFrom:
            - secretRef:
                name: {app_label}-secrets
            - configMapRef:
                name: {app_label}-config
          resources:
            requests:
              cpu: "100m"
              memory: "128Mi"
            limits:
              cpu: "{cpu_limit}"
              memory: "{memory_limit}"
          livenessProbe:
            httpGet:
              path: /health
              port: {port}
            initialDelaySeconds: 15
            periodSeconds: 20
            timeoutSeconds: 5
            failureThreshold: 3
          readinessProbe:
            httpGet:
              path: /health
              port: {port}
            initialDelaySeconds: 5
            periodSeconds: 10
            timeoutSeconds: 3
            failureThreshold: 3
          startupProbe:
            httpGet:
              path: /health
              port: {port}
            initialDelaySeconds: 5
            periodSeconds: 5
            failureThreshold: 12
          lifecycle:
            preStop:
              exec:
                command: ["/bin/sh", "-c", "sleep 5"]
"""

        # --- Service ---
        configs[
            "service.yaml"
        ] = f"""apiVersion: v1
kind: Service
metadata:
  name: {app_label}
  labels:
    app: {app_label}
spec:
  type: ClusterIP
  selector:
    app: {app_label}
  ports:
    - name: http
      port: 80
      targetPort: {port}
      protocol: TCP
"""

        # --- Ingress ---
        configs[
            "ingress.yaml"
        ] = f"""apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: {app_label}
  labels:
    app: {app_label}
  annotations:
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/proxy-body-size: "10m"
    nginx.ingress.kubernetes.io/proxy-read-timeout: "60"
    nginx.ingress.kubernetes.io/proxy-send-timeout: "60"
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  ingressClassName: nginx
  tls:
    - hosts:
        - {domain}
      secretName: {app_label}-tls
  rules:
    - host: {domain}
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: {app_label}
                port:
                  number: 80
"""

        # --- HPA ---
        configs[
            "hpa.yaml"
        ] = f"""apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: {app_label}
  labels:
    app: {app_label}
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: {app_label}
  minReplicas: {replicas}
  maxReplicas: {max(replicas * 5, 10)}
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 60
      policies:
        - type: Percent
          value: 50
          periodSeconds: 60
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
        - type: Percent
          value: 25
          periodSeconds: 120
"""

        # --- ConfigMap placeholder ---
        configs[
            "configmap.yaml"
        ] = f"""apiVersion: v1
kind: ConfigMap
metadata:
  name: {app_label}-config
  labels:
    app: {app_label}
data:
  NODE_ENV: "production"
  LOG_LEVEL: "info"
  PORT: "{port}"
"""

        # --- Secret placeholder ---
        configs[
            "secret.yaml"
        ] = f"""apiVersion: v1
kind: Secret
metadata:
  name: {app_label}-secrets
  labels:
    app: {app_label}
type: Opaque
stringData:
  DATABASE_URL: "postgresql://user:password@db:5432/{app_label}"
  # TODO: 替换为实际密钥值，建议使用 External Secrets Operator 或 Sealed Secrets
"""

        return configs

    # ------------------------------------------------------------------
    # Docker Compose 生产配置生成
    # ------------------------------------------------------------------

    def generate_docker_compose_production(
        self,
        port: int = 3000,
        db_port: int = 5432,
        redis_port: int = 6379,
    ) -> str:
        """生成带健康检查、资源限制、日志配置的 Docker Compose 生产配置。"""
        app_name = re.sub(r"[^a-z0-9-]", "-", self.name.lower())

        return f"""# Docker Compose 生产配置 - {self.name} v{self.version}
# 生成时间: 自动生成
# 使用方式: docker compose -f docker-compose.prod.yml up -d

version: "3.9"

services:
  app:
    image: {app_name}:v{self.version}
    container_name: {app_name}-app
    restart: unless-stopped
    ports:
      - "{port}:{port}"
    env_file:
      - .env.production
    environment:
      - NODE_ENV=production
      - PORT={port}
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:{port}/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    deploy:
      resources:
        limits:
          cpus: "1.0"
          memory: 512M
        reservations:
          cpus: "0.25"
          memory: 128M
    logging:
      driver: json-file
      options:
        max-size: "50m"
        max-file: "5"
        tag: "{app_name}-app"
    networks:
      - {app_name}-network

  postgres:
    image: postgres:16-alpine
    container_name: {app_name}-postgres
    restart: unless-stopped
    ports:
      - "{db_port}:5432"
    environment:
      POSTGRES_DB: {app_name}
      POSTGRES_USER: ${{DB_USER:-{app_name}}}
      POSTGRES_PASSWORD: ${{DB_PASSWORD:?DB_PASSWORD is required}}
      PGDATA: /var/lib/postgresql/data/pgdata
    volumes:
      - postgres-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${{DB_USER:-{app_name}}}"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 30s
    deploy:
      resources:
        limits:
          cpus: "1.0"
          memory: 1G
        reservations:
          cpus: "0.25"
          memory: 256M
    logging:
      driver: json-file
      options:
        max-size: "30m"
        max-file: "3"
    networks:
      - {app_name}-network

  redis:
    image: redis:7-alpine
    container_name: {app_name}-redis
    restart: unless-stopped
    ports:
      - "{redis_port}:6379"
    command: >
      redis-server
      --maxmemory 128mb
      --maxmemory-policy allkeys-lru
      --requirepass ${{REDIS_PASSWORD:-changeme}}
      --appendonly yes
    volumes:
      - redis-data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "-a", "${{REDIS_PASSWORD:-changeme}}", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    deploy:
      resources:
        limits:
          cpus: "0.5"
          memory: 256M
        reservations:
          cpus: "0.1"
          memory: 64M
    logging:
      driver: json-file
      options:
        max-size: "20m"
        max-file: "3"
    networks:
      - {app_name}-network

  nginx:
    image: nginx:1.25-alpine
    container_name: {app_name}-nginx
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/conf.d:/etc/nginx/conf.d:ro
      - ./certbot/conf:/etc/letsencrypt:ro
      - ./certbot/www:/var/www/certbot:ro
    depends_on:
      app:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "nginx", "-t"]
      interval: 30s
      timeout: 10s
      retries: 3
    deploy:
      resources:
        limits:
          cpus: "0.5"
          memory: 128M
    logging:
      driver: json-file
      options:
        max-size: "30m"
        max-file: "5"
    networks:
      - {app_name}-network

volumes:
  postgres-data:
    driver: local
  redis-data:
    driver: local

networks:
  {app_name}-network:
    driver: bridge
"""

    # ------------------------------------------------------------------
    # Nginx 反向代理配置生成
    # ------------------------------------------------------------------

    def generate_nginx_config(
        self,
        domain: str = "",
        upstream_port: int = 3000,
        enable_ssl: bool = True,
        enable_rate_limit: bool = True,
    ) -> str:
        """生成 Nginx 反向代理配置（含安全头、gzip、速率限制）。"""
        domain = domain or f"{self.name}.example.com"
        app_name = re.sub(r"[^a-z0-9-]", "-", self.name.lower())

        rate_limit_zone = ""
        rate_limit_directive = ""
        if enable_rate_limit:
            rate_limit_zone = f"""
    # 速率限制：每个 IP 每秒 10 个请求，突发允许 20
    limit_req_zone $binary_remote_addr zone={app_name}_limit:10m rate=10r/s;
    limit_req_zone $binary_remote_addr zone={app_name}_api_limit:10m rate=30r/s;
"""
            rate_limit_directive = f"""
        # 速率限制
        limit_req zone={app_name}_limit burst=20 nodelay;
        limit_req_status 429;
"""

        ssl_block = ""
        if enable_ssl:
            ssl_block = f"""
    # HTTPS 服务
    server {{
        listen 443 ssl http2;
        server_name {domain};

        ssl_certificate /etc/letsencrypt/live/{domain}/fullchain.pem;
        ssl_certificate_key /etc/letsencrypt/live/{domain}/privkey.pem;
        ssl_protocols TLSv1.2 TLSv1.3;
        ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
        ssl_prefer_server_ciphers off;
        ssl_session_cache shared:SSL:10m;
        ssl_session_timeout 1d;
        ssl_stapling on;
        ssl_stapling_verify on;

        # 安全头
        add_header X-Frame-Options "SAMEORIGIN" always;
        add_header X-Content-Type-Options "nosniff" always;
        add_header X-XSS-Protection "1; mode=block" always;
        add_header Referrer-Policy "strict-origin-when-cross-origin" always;
        add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
        add_header Content-Security-Policy "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' data:" always;
        add_header Permissions-Policy "camera=(), microphone=(), geolocation=()" always;
{rate_limit_directive}
        # API 路由
        location /api/ {{
            proxy_pass http://{app_name}_upstream;
            proxy_http_version 1.1;
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
            proxy_connect_timeout 10s;
            proxy_read_timeout 30s;
            proxy_send_timeout 30s;

            # API 专用速率限制
            {"limit_req zone=" + app_name + "_api_limit burst=50 nodelay;" if enable_rate_limit else ""}
        }}

        # 健康检查（不记录日志）
        location /health {{
            proxy_pass http://{app_name}_upstream;
            access_log off;
        }}

        # 静态文件
        location / {{
            root /usr/share/nginx/html;
            index index.html;
            try_files $uri $uri/ /index.html;

            # 静态资源缓存
            location ~* \\.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot)$ {{
                expires 1y;
                add_header Cache-Control "public, immutable";
                access_log off;
            }}
        }}

        # 禁止访问隐藏文件
        location ~ /\\. {{
            deny all;
            access_log off;
            log_not_found off;
        }}
    }}
"""

        return f"""# Nginx 配置 - {self.name} v{self.version}
# 生成时间: 自动生成

worker_processes auto;
worker_rlimit_nofile 65535;

events {{
    worker_connections 4096;
    multi_accept on;
    use epoll;
}}

http {{
    charset utf-8;
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;
    client_max_body_size 10m;

    # 日志格式
    log_format main '$remote_addr - $remote_user [$time_local] "$request" '
                    '$status $body_bytes_sent "$http_referer" '
                    '"$http_user_agent" "$http_x_forwarded_for" '
                    'rt=$request_time';

    access_log /var/log/nginx/access.log main;
    error_log /var/log/nginx/error.log warn;

    # Gzip 压缩
    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_min_length 1024;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript image/svg+xml;
{rate_limit_zone}
    # 上游服务
    upstream {app_name}_upstream {{
        least_conn;
        server app:{upstream_port} max_fails=3 fail_timeout=30s;
        keepalive 32;
    }}

    # HTTP -> HTTPS 重定向
    server {{
        listen 80;
        server_name {domain};

        location /.well-known/acme-challenge/ {{
            root /var/www/certbot;
        }}

        location / {{
            return 301 https://$host$request_uri;
        }}
    }}
{ssl_block}}}
"""

    # ------------------------------------------------------------------
    # 环境变量模板生成
    # ------------------------------------------------------------------

    def generate_env_template(self) -> str:
        """生成 .env.example 模板，包含所有必要的环境变量说明。"""
        app_name = re.sub(r"[^a-z0-9_]", "_", self.name.lower())

        return f"""# ============================================
# {self.name} 环境变量模板
# 版本: {self.version}
# 生成时间: 自动生成
# ============================================
# 使用方式: cp .env.example .env && 编辑 .env 填入实际值
# 注意: .env 文件不应提交到版本控制
# ============================================

# ---- 应用配置 ----
NODE_ENV=production
PORT=3000
LOG_LEVEL=info
APP_NAME={self.name}
APP_VERSION={self.version}

# ---- 数据库配置 ----
DB_HOST=localhost
DB_PORT=5432
DB_NAME={app_name}
DB_USER={app_name}
DB_PASSWORD=          # 必填: 数据库密码（至少 16 位随机字符串）
DATABASE_URL=postgresql://${{DB_USER}}:${{DB_PASSWORD}}@${{DB_HOST}}:${{DB_PORT}}/${{DB_NAME}}

# ---- Redis 配置 ----
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=       # 必填: Redis 密码
REDIS_URL=redis://:${{REDIS_PASSWORD}}@${{REDIS_HOST}}:${{REDIS_PORT}}/0

# ---- 认证配置 ----
JWT_SECRET=           # 必填: JWT 签名密钥（至少 256 位随机字符串）
JWT_EXPIRES_IN=15m    # Access token 过期时间
JWT_REFRESH_EXPIRES_IN=7d  # Refresh token 过期时间
SESSION_SECRET=       # 必填: Session 密钥

# ---- CORS 配置 ----
CORS_ORIGINS=https://{self.name}.example.com  # 允许的跨域源（逗号分隔）
CORS_CREDENTIALS=true

# ---- 邮件配置 ----
SMTP_HOST=
SMTP_PORT=587
SMTP_USER=
SMTP_PASSWORD=        # 必填: SMTP 密码
SMTP_FROM={self.name}@example.com

# ---- 对象存储 ----
S3_BUCKET=
S3_REGION=
AWS_ACCESS_KEY_ID=    # 必填: AWS Access Key
AWS_SECRET_ACCESS_KEY= # 必填: AWS Secret Key

# ---- 第三方服务 ----
SENTRY_DSN=           # 可选: Sentry 错误追踪
STRIPE_SECRET_KEY=    # 按需: 支付密钥
SENDGRID_API_KEY=     # 按需: 邮件服务

# ---- 部署配置 ----
DOMAIN={self.name}.example.com
SSL_ENABLED=true
HEALTH_CHECK_PATH=/health

# ---- 日志配置 ----
LOG_FORMAT=json       # json | text
LOG_FILE=/var/log/{app_name}/app.log
LOG_MAX_SIZE=50m
LOG_MAX_FILES=5
"""

    def write_deploy_configs(self) -> dict[str, str]:
        """将所有部署配置写入 output/deploy/ 目录，返回文件路径映射。"""
        deploy_dir = self.project_dir / "output" / "deploy"
        deploy_dir.mkdir(parents=True, exist_ok=True)

        written: dict[str, str] = {}

        # K8s 配置
        k8s_dir = deploy_dir / "kubernetes"
        k8s_dir.mkdir(parents=True, exist_ok=True)
        for filename, content in self.generate_kubernetes_configs().items():
            file_path = k8s_dir / filename
            file_path.write_text(content, encoding="utf-8")
            written[f"kubernetes/{filename}"] = str(file_path)

        # Docker Compose 生产配置
        compose_path = deploy_dir / "docker-compose.prod.yml"
        compose_path.write_text(self.generate_docker_compose_production(), encoding="utf-8")
        written["docker-compose.prod.yml"] = str(compose_path)

        # Nginx 配置
        nginx_path = deploy_dir / "nginx.conf"
        nginx_path.write_text(self.generate_nginx_config(), encoding="utf-8")
        written["nginx.conf"] = str(nginx_path)

        # 环境变量模板
        env_path = deploy_dir / ".env.example"
        env_path.write_text(self.generate_env_template(), encoding="utf-8")
        written[".env.example"] = str(env_path)

        return written

    def _collect_spec_task_summary(self) -> dict[str, int | str]:
        task_files = list((self.project_dir / ".super-dev" / "changes").glob("*/tasks.md"))
        selected_files: list[Path] = []
        selected_change = ""
        named_file = self.project_dir / ".super-dev" / "changes" / self.name / "tasks.md"
        if named_file.exists():
            selected_files = [named_file]
            selected_change = self.name
        elif task_files:
            latest_file = max(task_files, key=lambda path: path.stat().st_mtime)
            selected_files = [latest_file]
            selected_change = latest_file.parent.name
        total = 0
        completed = 0
        in_progress = 0
        for task_file in selected_files:
            for line in task_file.read_text(encoding="utf-8", errors="ignore").splitlines():
                stripped = line.strip()
                if not stripped.startswith("- ["):
                    continue
                status = stripped[2:5]
                if not re.match(r"^\[[ x~_]\]$", status):
                    continue
                total += 1
                if status == "[x]":
                    completed += 1
                elif status == "[~]":
                    in_progress += 1
        pending = max(0, total - completed)
        return {
            "task_files": len(selected_files),
            "total": total,
            "completed": completed,
            "pending": pending,
            "in_progress": in_progress,
            "target_change": selected_change,
        }
