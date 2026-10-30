# FiboLab：学生答题与教师排行榜

本次集成沿用了同学提供的 FiboLab 视觉设计，替换了原来的正则判分、演示登录和 ChatGPT Sites/D1 后端。学生填名字即可加入；不需要 ChatGPT 账号、密码或邀请码。

## 演出用一键入口

请优先看根目录的「演示当天只看这里.md」。当前用户的 Mac 可双击「开始演示.command」连接 `factlab-dev0-out`，自动打开课件和教师页面；学生二维码随本次网址自动更新。双击「结束演示.command」停止，默认 4 小时自动关闭。此模式使用服务器现有 Bubblewrap + Python 3.9，不需要启动 Docker，也无需永久安装服务。普通长期部署仍可按下文使用 Docker。

## 课件入口

- 第 6 页：学生二维码和「Open FiboLab」链接。
- 第 8 页：嵌入自动刷新的只读排行榜，以及完整教师页面链接。
- 学生页面：`lab/`；教师页面：`lab/?view=teacher`。
- 二维码默认随实际打开课件的网址自动生成，使用本地附带的 QR 库；旧的 PNG 仅作脚本失败时的 GitHub Pages 回退。临时地址、局域网地址无需手动改二维码。

## 部署关系

```text
学生浏览器 ── 打开 GitHub Pages 的 lab/ ── HTTPS API ── Python 服务
教师课件   ── 嵌入 lab/?view=teacher ───── 同一个 API ─── SQLite
                                                     └─ Docker 执行 Python
```

**代码合入不等于后端已上线。** 还需在一台学生和教师都能访问的 Linux 服务器上启动服务，并填写 API 地址。仓库中不包含服务器账号、域名或生产教师密钥。

推荐两种部署方式：

1. **保留 GitHub Pages 课件**：服务器只负责 API；将 `lab/config.js` 的 `FIBOLAB_API_BASE` 改成实际 HTTPS 后端地址，例如 `https://fibo.example.edu`，不带 `/api` 后缀。服务器的允许来源设为 `https://sun123-cmd.github.io`，不带 `/pdev` 路径。学生与教师必须访问同一个前端版本。
2. **课件和 API 同源部署**：本服务也能提供课件和 `lab/` 静态文件；`FIBOLAB_API_BASE` 保持空字符串即可。把二维码改成新前端地址。此方式也便于在校园网内部统一访问。

HTTPS 课件不能调用普通 HTTP 后端。校园网服务器可以放在学校现有 HTTPS 网关后面，或使用学生设备信任的学校证书。只开一个 HTTP IP 端口，不能直接接到 GitHub Pages 上。部署前请分别用学生 Wi-Fi、教师网络测试可达性。

## 本机启动 / 服务器手动启动

以下是手动 Docker 部署方式（非一键演出模式）：Python 3.11+、可运行 Linux 容器的 Docker、可拉取 Python 镜像。API 本身只用 Python 标准库，不需要 pip 依赖。

在仓库根目录：

```bash
docker build -f service/Dockerfile.judge -t fibolab-judge:local .
export FIBOLAB_ADMIN_TOKEN="$(python3 -c 'import secrets; print(secrets.token_urlsafe(32))')"
export FIBOLAB_DB="$PWD/data/fibolab.sqlite"
export FIBOLAB_ALLOWED_ORIGINS="http://127.0.0.1:8080,http://localhost:8080"
python3 -m service.server --host 127.0.0.1 --port 8080
```

打开 `http://127.0.0.1:8080/` 看课件，`http://127.0.0.1:8080/lab/` 答题。教师密钥保存在启动环境中；需要时在启动服务的终端查看 `FIBOLAB_ADMIN_TOKEN`，然后输入教师页面的「Teacher access key」。请保管密钥，不要放进前端 JS 或提交到 Git。

服务启动时会检查 Docker 与判题镜像；没有镜像就会退出，不会退回到宿主机执行学生代码。`GET /api/health` 同时检查判题镜像能否访问。

镜像仓库访问受限时，可以将官方 Python 镜像离线传入服务器，或使用学校维护的 Python 镜像：

```bash
docker build --build-arg PYTHON_IMAGE=your-approved-python-image:tag \
  -f service/Dockerfile.judge -t fibolab-judge:local .
```

## Linux 常驻运行

以下示例假设 Docker 与 Python 3.11+ 已安装，代码放在 `/opt/pdev`；按服务器实际发行版调整 Python 路径。

```bash
sudo useradd --system --create-home --home-dir /var/lib/fibolab fibolab
sudo install -d -o fibolab -g fibolab /var/lib/fibolab
cd /opt/pdev
sudo docker build -f service/Dockerfile.judge -t fibolab-judge:local .
sudo install -m 600 /dev/null /etc/fibolab.env
sudoedit /etc/fibolab.env
```

在 `/etc/fibolab.env` 中填写：

```ini
FIBOLAB_ADMIN_TOKEN=replace-with-a-long-random-teacher-key
FIBOLAB_DB=/var/lib/fibolab/fibolab.sqlite
FIBOLAB_ALLOWED_ORIGINS=https://sun123-cmd.github.io,https://fibo.example.edu
FIBOLAB_JUDGE_IMAGE=fibolab-judge:local
```

将示例域名替换成实际域名。教师密钥至少 16 个字符，建议用上面的 `secrets.token_urlsafe(32)` 生成。然后：

```bash
sudo install -m 644 service/fibolab.service /etc/systemd/system/fibolab.service
sudo systemctl daemon-reload
sudo systemctl enable --now fibolab
sudo systemctl status fibolab
curl http://127.0.0.1:8080/api/health
```

服务默认只监听服务器回环地址，由 HTTPS 反向代理对外提供访问。`service/Caddyfile.example` 提供 Caddy 示例；自动签发证书需要相应的 DNS 与公网验证条件。只有校园网内可访问的服务器，优先使用学校现有 HTTPS 网关或证书。更新代码后重新构建判题镜像，并重启 `fibolab` 服务。

## 题目与排名规则

```python
def fibonacci(n):
    # Return the first n terms as a list, starting with 0 and 1.
    ...
```

- 实际在 Python 中调用函数，检查 `n = 0, 1, 2, 8, 20` 的返回列表，每项 8 分，共 40 分。
- AST 检查函数体是否有循环（`for`、`while` 或列表推导），共 10 分。禁止递归、导入、顶层代码与本题不需要的调用。允许 `range/len/list/tuple/enumerate/zip/min/max/abs/sum/reversed` 和列表 `append/extend`。内置函数名不能重新赋值。这是本课堂练习的语言范围，不是通用 OJ。
- 只有五项结果全对且有循环才标为 Passed。语法错误、运行错误、错误返回值、无限循环不会显示通过。
- 不再声称自动评估复杂度或可读性。循环检查只识别语法结构，TA 仍需确认循环是否真正完成计算，并听学生解释状态更新。
- 服务器在接受提交时记录顺序；通过后按首次正确尝试的提交顺序排名，不按判题完成快慢排名。
- 所有尝试保留；后续错误提交不会覆盖已通过成绩或首次通过时间。排行榜也会显示最新尝试是否需要修改。
- TA 在教师页面输入访问密钥，点击学生的 Review，查看首次通过的代码和提交历史，听完解释后点击 Confirm explanation。
- 同分不再让较晚提交的人排到前面。TA 确认不改变自动排名。

## 数据与身份

学生注册得到随机令牌，只保存在当前浏览器的 localStorage，服务器保存令牌哈希；没有公开学生令牌。刷新页面保留注册和本地草稿。清理浏览器存储、换浏览器或点击 Change student 后需要重新注册，可能生成另一条学生记录；这是面向几位同学课堂使用的轻量身份，不做学号验证或跨设备账号恢复。

SQLite 保存姓名、每次代码、测试结果、提交时间和确认状态。公开排行榜仅返回姓名、分数和状态，不返回代码。教师查看代码和确认操作需要服务器密钥。教师密钥仅在当前标签页的 sessionStorage 中保留，点 Lock review 可清除。

一键演出模式用 Bubblewrap 隔离进程：不挂载用户主目录、隐藏环境变量、独立网络与进程命名空间、128 MB 虚拟内存上限、2 秒 CPU 上限和 5 秒墙钟超时。只挂载 Python 运行时与判题脚本；没有宿主机直接执行回退。以下资源参数指 Docker 模式。

服务最多同时执行 2 份代码，同一学生只接受一份正在执行的提交。繁忙时返回稍后重试提示；执行中的尝试会显示 Judging。判题容器无网络、非 root、只读文件系统、96 MB 内存、1 CPU、32 进程上限和 5 秒墙钟超时；超时后移除容器。服务重启后未完成的尝试会标为中断，提示重新提交。

保留 `fibolab.sqlite`、`-wal`、`-shm` 在同一目录。备份推荐在服务器停止服务后复制数据库；下一次课需要全新排行榜时，先停止服务并归档数据库文件，再启动服务。不要把学生数据库提交到仓库。

## 验证

```bash
python3 -m unittest discover -s tests -v
FIBOLAB_DOCKER_TESTS=1 python3 -m unittest discover -s tests -v
```

第二条会真正启动 Docker 判题，需要先构建镜像。默认命令会跳过需要隔离工具的用例。Linux 实验室服务器可运行 `FIBOLAB_BWRAP_TESTS=1 python3 -m unittest discover -s tests -v`，其中四项 HTTP 集成用例会改用真实 Bubblewrap 判题。测试覆盖正确/错误输出、边界、语法错误、递归与导入限制、无限循环、注册令牌、跨来源请求、教师权限、排名持久化和并发提交顺序。

浏览器测试需要 Node.js、Playwright 与 Chrome；在另一个终端启动全新的测试实例后执行：

```bash
npm install --prefix /tmp/fibolab-browser-check playwright
NODE_PATH=/tmp/fibolab-browser-check/node_modules node tests/browser/lab.cjs
NODE_PATH=/tmp/fibolab-browser-check/node_modules node tests/browser/slides.cjs
```

浏览器测试默认连接 `http://127.0.0.1:8080`，可通过 `FIBOLAB_TEST_URL` 修改；测试实例使用教师密钥 `local-teacher-testing-2026`。测试会创建学生、提交代码和确认讲解，只对临时测试数据库运行。

测试说明：开发环境无法访问 Docker Hub，因此本次容器测试使用本机已有 Python 3.10 镜像作为基础构建判题镜像；API 使用 Python 3.13。默认发布 Dockerfile 使用官方 `python:3.12-slim`，该基础镜像的重新拉取和目标校园服务器部署尚未验证。学生/教师两个独立浏览器会话已验证提交、共享排行榜、教师查看/确认、草稿持久化、离线提示和手机布局；课件检查覆盖两个 HTML 入口、导航与嵌入排行榜。测试中的 Mentimeter 网络加载被隔离，不代表本次重新验证了第三方投票服务。

一键模式补充验证（2026-10-30）：`factlab-dev0-out` 上 Python 3.9 + Bubblewrap 的 22 项测试全部通过；本机 Docker 模式 21 项通过、1 项 Linux 专用测试跳过。临时 HTTPS 和本机局域网入口都完成了独立学生/教师浏览器联调，包含自动教师解锁、动态二维码和公开元数据不泄露教师密钥。已实际验证自动关闭发生在无限循环判题期间时仍能完成清理。联调服务已停止，彩排数据库已归档；演出现场 Wi-Fi/学生手机尚需提前彩排确认。
