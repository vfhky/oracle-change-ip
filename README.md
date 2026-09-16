# oracle-change-ip

Oracle OCI 公网 IP 自动轮换工具。当检测到当前公网 IP 在中国大陆被封锁时，自动申请新 IP 并释放旧 IP，保障服务可访问性。

## 功能特性

- **多源检测**：同时调用 [ping.pe](https://ping.pe) 和 [ipcheck.ing](https://ipcheck.ing) 两个第三方 API，从中国大陆节点判断 IP 可达性，避免在 OCI 机器上自检产生的误判
- **投票机制**：需要 ≥2 个数据源同时判定封锁才触发轮换，降低误操作风险
- **TCP 兜底**：第三方 API 均不可用时，退化为本地 TCP 探测
- **安全轮换**：先申请新 IP，再解绑并释放旧 IP，避免实例瞬间断网
- **一键运行**：`run.sh` 自动完成 Python 版本检测、虚拟环境创建、依赖安装
- **零硬编码**：所有配置通过 `.env` 文件注入，敏感信息不进入版本控制

## 快速开始

### 前置条件

- Python 3.8+
- OCI CLI 配置文件 `~/.oci/config`（参考 [OCI 官方文档](https://docs.oracle.com/en-us/iaas/Content/API/Concepts/sdkconfig.htm)）

### 安装与运行

```bash
# 克隆仓库
git clone https://github.com/<your-username>/oracle-change-ip.git
cd oracle-change-ip

# 首次运行：自动创建虚拟环境、安装依赖，并生成 .env 模板
./run.sh

# 编辑 .env，填写你的实例 OCID
vi .env

# 再次运行即开始检测并按需轮换
./run.sh

# 模拟运行（不执行任何 OCI 写操作）
./run.sh --dry-run
```

### 配置说明

复制 `.env.example` 为 `.env` 并填写以下字段：

| 变量 | 必填 | 默认值 | 说明 |
|------|------|--------|------|
| `OCI_INSTANCE_ID` | ✅ | — | OCI 实例的 OCID |
| `OCI_CONFIG_PROFILE` | — | `DEFAULT` | `~/.oci/config` 中的配置块名称 |
| `CHECK_PORT` | — | `22` | TCP 兜底探测端口 |
| `CHECK_TIMEOUT` | — | `5` | API / TCP 请求超时秒数 |

> `.env` 文件包含敏感信息，已加入 `.gitignore`，**请勿提交到版本控制**。

## 项目结构

```
oracle-change-ip/
├── main.py          # 入口：参数解析、OCI 客户端初始化、主流程编排
├── config.py        # 配置加载：从环境变量读取并校验参数
├── checker.py       # IP 可达性检测：多源投票 + TCP 兜底
├── rotator.py       # IP 轮换：安全的创建→解绑→释放流程
├── run.sh           # 一键启动脚本（含环境自动配置）
├── requirements.txt # Python 依赖
├── .env.example     # 配置模板
└── tests/           # 单元测试（pytest）
```

## IP 轮换逻辑

```
检测 IP 可达性
    ├─ ping.pe API    ┐
    └─ ipcheck.ing API┘ → ≥2 源判定封锁 → 触发轮换
           ↓（均不可用）
         TCP 兜底探测

轮换流程（OCI）：
  1. create_public_ip（新 IP 绑定到私有 IP）
  2. update_public_ip（将旧 IP 的 private_ip_id 置空，解绑）
  3. delete_public_ip（释放旧保留 IP）
  4. 轮询等待旧 IP 状态变为 TERMINATED
```

## 定时执行

推荐通过 crontab 定期运行（例如每小时检测一次）：

```bash
# crontab -e
0 * * * * cd /path/to/oracle-change-ip && ./run.sh >> /var/log/oracle-change-ip.log 2>&1
```

## 开发与测试

```bash
# 运行全部测试
pytest -v

# 模拟运行（不写 OCI）
./run.sh --dry-run
```

## 许可证

MIT
