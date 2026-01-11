# Jupyter 学习环境使用指南

## 快速启动

### 方法一：使用 JupyterLab（推荐，支持代码提示）⭐

```bash
cd learn_docs
./start_jupyterlab.sh
```

**优势**：
- ✅ 完整的代码自动补全
- ✅ 函数参数提示
- ✅ 类型提示支持
- ✅ 更好的 IDE 体验

### 方法二：使用传统 Jupyter Notebook

```bash
cd learn_docs
./start_jupyter.sh
```

**注意**：传统 Jupyter Notebook 的代码提示功能有限，建议使用 JupyterLab。

### 方法三：使用 VS Code（最推荐）⭐⭐⭐

1. 在 VS Code 中打开项目目录
2. 直接打开 `.ipynb` 文件
3. 享受完整的 IDE 体验（代码提示、参数提示、类型提示）

### 方法四：手动启动

```bash
# 确保已安装 jupyter
pip install jupyter ipykernel

# 在项目根目录启动
cd /Users/zhenzhang/workspace/qlib
jupyter notebook
```

## 学习用的 Notebook

### 主要学习 Notebook

- **`learn_docs/qlib_学习.ipynb`** - 专门为学习设计，包含：
  - 环境初始化
  - 数据测试与验证
  - 训练样本构建
  - 自定义特征工程
  - 数据可视化

### 官方示例 Notebook

- **`examples/workflow_by_code.ipynb`** - 完整的工作流示例
- **`examples/tutorial/detailed_workflow.ipynb`** - 详细教程
- **`examples/rl/simple_example.ipynb`** - 强化学习示例

## 使用步骤

1. **启动 Jupyter 服务**
   ```bash
   ./learn_docs/start_jupyter.sh
   ```

2. **打开浏览器**
   - 访问 `http://localhost:8888`
   - 如果提示输入 token，在终端中查找并复制

3. **打开学习 Notebook**
   - 导航到 `learn_docs/qlib_学习.ipynb`
   - 开始交互式学习

4. **配置数据路径**
   - 在 notebook 的第一个代码 cell 中，根据你的实际数据路径修改 `provider_uri`
   - 例如：`provider_uri = "~/.qlib/qlib_data/cn_data"`

## 注意事项

1. **数据路径配置**
   - 确保你的 tushare 数据已经正确导入到 qlib 格式
   - 在 notebook 中修改 `provider_uri` 指向正确的数据路径

2. **依赖安装**
   - 如果缺少某些库，可以在 notebook 中使用 `!pip install package_name` 安装

3. **保存工作**
   - Jupyter 会自动保存 notebook
   - 建议定期保存重要结果

4. **停止服务**
   - 在终端中按 `Ctrl+C` 停止 Jupyter 服务

## 学习路径建议

1. **数据测试阶段**（当前阶段）
   - 使用 `qlib_学习.ipynb` 的"数据测试与验证"部分
   - 验证数据加载是否正常
   - 检查数据质量

2. **训练样本构建**
   - 使用"训练样本构建"部分
   - 根据需求调整特征和标签配置
   - 验证数据集创建是否成功

3. **特征工程**
   - 使用"自定义特征工程"部分
   - 添加更多技术指标
   - 构建自定义因子

4. **模型训练**
   - 参考 `examples/benchmarks/` 下的模型示例
   - 使用构建好的数据集进行训练

5. **回测验证**
   - 参考 `examples/workflow_by_code.ipynb`
   - 使用 qlib 的回测框架验证策略

## 代码提示和自动补全

### 在 Jupyter Notebook 中

使用以下快捷键：
- `Tab` - 触发自动补全
- `Shift+Tab` - 查看函数签名和文档
- `Shift+Tab+Tab` - 查看完整文档

### 在 JupyterLab 中

1. **安装 LSP 扩展**（如果未安装）：
   ```bash
   pip install jupyterlab-lsp 'python-lsp-server[all]'
   ```

2. **使用**：
   - 代码提示：输入时自动显示
   - 参数提示：输入 `(` 后自动显示函数签名
   - 类型提示：悬停变量/函数查看类型信息

### 在 VS Code 中

- 代码提示：自动工作
- 参数提示：输入 `(` 时自动显示
- 类型提示：悬停查看

**详细配置请参考**：`learn_docs/配置代码提示.md`

## 常见问题

### Q: 如何启用代码提示？
A: 推荐使用 JupyterLab 或 VS Code。详细配置请查看 `learn_docs/配置代码提示.md`

### Q: Jupyter 启动后无法访问？
A: 检查防火墙设置，确保 8888 端口未被占用。可以尝试使用其他端口：
```bash
jupyter notebook --port 8889
```

### Q: 导入 qlib 失败？
A: 确保已正确安装 qlib：
```bash
pip install pyqlib
# 或从源码安装
pip install -e .
```

### Q: 数据加载失败？
A: 检查数据路径是否正确，确保数据已经正确导入：
```python
# 在 notebook 中检查
import qlib
from qlib.data import D
instruments = D.instruments()
print(f"可用股票数量: {len(instruments)}")
```

## 更多资源

- Qlib 官方文档：查看 `docs/` 目录
- 学习计划：查看 `learn_docs/学习计划.md`
- 安装指南：查看 `learn_docs/安装指南.md`

