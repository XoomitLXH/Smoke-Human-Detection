# 将项目上传到 GitHub 完整指南

## 一、上传前准备（建议）

### 1. 忽略大模型文件（避免仓库过大、推送超时）

模型文件 `*.pth`、`*.pt` 通常很大，建议不提交到 Git。请编辑 `.gitignore`，取消下面几行的注释（删掉行首的 `#`）：

```
# 把这 4 行前面的 # 删掉：
*.pth
*.pt
# fusion_model.pth
# rtdetr-l.pt
```

这样 `fusion_model.pth`、`rtdetr-l.pt`、`smoke_detect.pt` 就不会被上传。如需别人使用，可在 README 里写「模型需自行下载」。

---

## 二、在 GitHub 上创建仓库

1. 打开 [https://github.com/new](https://github.com/new)
2. **Repository name**：填 `A25-Smoke-Human-Detection-Demo`（或你喜欢的名字）
3. **Description**：可选，如「烟雾与人体检测演示」
4. 选择 **Public**
5. **不要**勾选 "Add a README file"（本地已有）
6. 点击 **Create repository**

创建完成后，页面上会显示仓库地址，类似：  
`https://github.com/你的用户名/A25-Smoke-Human-Detection-Demo.git`

---

## 三、在本地用 Git 上传

在 **PowerShell** 或 **终端** 里，进入项目目录后依次执行下面的命令。

### 步骤 1：进入项目目录（如已在可跳过）

```powershell
cd e:\A25-Smoke-Human-Detection-Demo
```

### 步骤 2：添加要提交的文件

```powershell
git add .
```

（`.` 表示当前目录下所有未忽略的文件）

### 步骤 3：第一次提交

```powershell
git commit -m "Initial commit: 烟雾与人体检测项目"
```

### 步骤 4：添加 GitHub 远程仓库

把下面的 `你的用户名` 换成你的 GitHub 用户名：

```powershell
git remote add origin https://github.com/你的用户名/A25-Smoke-Human-Detection-Demo.git
```

如果仓库名不同，把 `A25-Smoke-Human-Detection-Demo` 改成你创建时的仓库名。

### 步骤 5：推送到 GitHub

```powershell
git branch -M main
git push -u origin main
```

- 第一次推送可能会弹出浏览器或提示你登录 GitHub。
- 如提示用 **Personal Access Token**，请到 GitHub → Settings → Developer settings → Personal access tokens 生成一个，用 token 代替密码。

---

## 四、以后更新代码怎么上传？

修改代码后，在项目目录执行：

```powershell
git add .
git commit -m "这里写你做了啥修改"
git push
```

---

## 五、常见问题

| 问题 | 处理 |
|------|------|
| 提示 `conda init` | 可忽略，不影响 git。或先执行 `conda init powershell` 再开新终端。 |
| 推送时要求登录 | 用 GitHub 用户名 + Personal Access Token（不再用密码）。 |
| 推送很慢或超时 | 检查是否提交了 `.pth`/`.pt` 大文件，用 `.gitignore` 排除后再提交。 |
| 已提交了大文件想删掉 | 需要从历史中移除，可搜索「git 删除已提交的大文件」。 |

---

按「二 → 三」顺序做一遍，就可以把项目整体上传到 GitHub。
