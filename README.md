# Distance Curve Tools

GROMACS 分子动力学**距离-时间曲线**的后处理工具集，包含噪声增强批处理与交互式曲线编辑器。

## 工具

### 1. `augment_gui.py` — 批量曲线增强

按配置文件对距离 CSV 分段添加 Perlin / 高斯 / 正弦等扰动，输出 CSV 和 XVG。

```bash
python src/augment_gui.py \
  --input examples/sample_input.csv \
  --config examples/config.example.json \
  --output output/augmented.csv
```

### 2. `curve_editor.py` — 交互式曲线编辑器

基于 PyQt5 + pyqtgraph 的 GUI，支持拖拽编辑、撤销/重做、读写 XVG/CSV。

```bash
python src/curve_editor.py
```

### 3. `perlin_noise.py` — 一维 Perlin 噪声

供 `augment_gui.py` 调用的噪声生成模块。

## 安装

```bash
pip install -r requirements.txt
```

## 配置说明

`examples/config.example.json` 定义全局裁剪范围与各时间段的扰动参数：

- `global_clip`: 距离值裁剪区间（Å）
- `regions`: 时间段列表，每段可设置 `mode`（`sin` / `sin_noise` / `gaussian` / `perlin` / `spike`）、`amp`（振幅）、`pts`（插值点数）

## License

MIT
